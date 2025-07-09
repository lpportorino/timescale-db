package main

import (
	"bufio"
	"context"
	"database/sql"
	"flag"
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"time"

	_ "github.com/lib/pq"
)

const (
	colorGreen  = "\033[0;32m"
	colorYellow = "\033[1;33m"
	colorRed    = "\033[0;31m"
	colorBlue   = "\033[0;34m"
	colorReset  = "\033[0m"
)

type Config struct {
	Host       string
	Port       int
	User       string
	Password   string
	Database   string
	BackupDir  string
	Format     string
	Compress   int
	NoProgress bool
	Checkpoint string
	DryRun     bool
}

func main() {
	config := parseFlags()

	if err := run(config); err != nil {
		log.Fatal(err)
	}
}

func parseFlags() *Config {
	config := &Config{}

	flag.StringVar(&config.Host, "host", getEnv("PGHOST", "localhost"), "PostgreSQL host")
	flag.IntVar(&config.Port, "port", getEnvInt("PGPORT", 5432), "PostgreSQL port")
	flag.StringVar(&config.User, "user", getEnv("PGUSER", "postgres"), "PostgreSQL user")
	flag.StringVar(&config.Password, "password", getEnv("PGPASSWORD", ""), "PostgreSQL password")
	flag.StringVar(&config.Database, "database", getEnv("PGDATABASE", "postgres"), "PostgreSQL database")
	flag.StringVar(&config.BackupDir, "backup-dir", "backups", "Backup directory")
	flag.StringVar(&config.Format, "format", "tar", "Backup format (tar or plain)")
	flag.IntVar(&config.Compress, "compress", 6, "Compression level (0-9)")
	flag.BoolVar(&config.NoProgress, "no-progress", false, "Disable progress reporting")
	flag.StringVar(&config.Checkpoint, "checkpoint", "fast", "Checkpoint mode (fast or spread)")
	flag.BoolVar(&config.DryRun, "dry-run", false, "Dry run mode")

	flag.Parse()

	// Set PGPASSWORD environment variable if password is provided
	if config.Password != "" {
		os.Setenv("PGPASSWORD", config.Password)
	}

	return config
}

func run(config *Config) error {
	printMsg(colorGreen, "PostgreSQL Cluster Backup (pg_basebackup)")
	fmt.Println(strings.Repeat("=", 50))

	// Test connection and check replication permission
	if err := testConnection(config); err != nil {
		return fmt.Errorf("connection test failed: %w", err)
	}

	// Estimate database size
	size, err := estimateSize(config)
	if err != nil {
		printMsg(colorYellow, "Warning: Could not estimate database size: "+err.Error())
	} else {
		printMsg(colorBlue, fmt.Sprintf("Estimated database size: %s", formatBytes(size)))
	}

	// Create backup
	backupPath, err := createBackup(config)
	if err != nil {
		return fmt.Errorf("backup failed: %w", err)
	}

	// Verify backup
	if err := verifyBackup(config, backupPath); err != nil {
		return fmt.Errorf("backup verification failed: %w", err)
	}

	printMsg(colorGreen, "\n✓ Backup completed successfully!")
	printMsg("", fmt.Sprintf("Location: %s", backupPath))

	return nil
}

func testConnection(config *Config) error {
	connStr := fmt.Sprintf("host=%s port=%d user=%s password=%s dbname=%s sslmode=disable",
		config.Host, config.Port, config.User, config.Password, config.Database)

	db, err := sql.Open("postgres", connStr)
	if err != nil {
		return err
	}
	defer db.Close()

	// Test connection
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := db.PingContext(ctx); err != nil {
		return err
	}

	// Check replication permission
	var hasReplication bool
	err = db.QueryRow("SELECT rolreplication FROM pg_roles WHERE rolname = $1", config.User).Scan(&hasReplication)
	if err != nil {
		return fmt.Errorf("failed to check replication permission: %w", err)
	}

	if !hasReplication {
		return fmt.Errorf("user '%s' does not have REPLICATION permission", config.User)
	}

	printMsg(colorGreen, fmt.Sprintf("✓ Connected to %s:%d as %s", config.Host, config.Port, config.User))
	printMsg(colorGreen, "✓ User has REPLICATION permission")

	return nil
}

func estimateSize(config *Config) (int64, error) {
	connStr := fmt.Sprintf("host=%s port=%d user=%s password=%s dbname=%s sslmode=disable",
		config.Host, config.Port, config.User, config.Password, config.Database)

	db, err := sql.Open("postgres", connStr)
	if err != nil {
		return 0, err
	}
	defer db.Close()

	var size sql.NullInt64
	err = db.QueryRow(`
		SELECT SUM(pg_database_size(datname))::bigint 
		FROM pg_database 
		WHERE NOT datistemplate
	`).Scan(&size)

	if err != nil {
		return 0, err
	}

	if !size.Valid {
		return 0, fmt.Errorf("could not determine database size")
	}

	return size.Int64, nil
}

func createBackup(config *Config) (string, error) {
	// Create timestamped backup directory
	timestamp := time.Now().Format("20060102_150405")
	backupName := fmt.Sprintf("cluster_backup_%s", timestamp)
	backupPath := filepath.Join(config.BackupDir, backupName)

	if config.DryRun {
		printMsg(colorYellow, "DRY RUN: Would create backup in "+backupPath)
		return backupPath, nil
	}

	// Create backup directory
	if err := os.MkdirAll(backupPath, 0755); err != nil {
		return "", fmt.Errorf("failed to create backup directory: %w", err)
	}

	printMsg(colorBlue, fmt.Sprintf("\nStarting backup to: %s", backupPath))

	// Build pg_basebackup command
	args := []string{
		"-h", config.Host,
		"-p", strconv.Itoa(config.Port),
		"-U", config.User,
		"-D", backupPath,
		"-c", config.Checkpoint,
	}

	if config.Format == "tar" {
		args = append(args, "-Ft")
		if config.Compress > 0 {
			args = append(args, "-z") // Use gzip compression for tar format
		}
	} else {
		args = append(args, "-Fp")
	}

	if !config.NoProgress {
		args = append(args, "-P")
	}

	// Stream WAL
	args = append(args, "-Xs", "-v")

	// Create command
	cmd := exec.Command("pg_basebackup", args...)
	
	// Capture output for progress
	if !config.NoProgress {
		stderr, err := cmd.StderrPipe()
		if err != nil {
			return "", err
		}

		// Start command
		if err := cmd.Start(); err != nil {
			return "", err
		}

		// Monitor progress
		scanner := bufio.NewScanner(stderr)
		progressRe := regexp.MustCompile(`(\d+)/(\d+)\s+kB\s+\((\d+)%\)`)
		
		for scanner.Scan() {
			line := scanner.Text()
			if matches := progressRe.FindStringSubmatch(line); matches != nil {
				current, _ := strconv.ParseInt(matches[1], 10, 64)
				total, _ := strconv.ParseInt(matches[2], 10, 64)
				percent := matches[3]
				
				fmt.Printf("\r%sProgress: %s%% (%s / %s)%s",
					colorBlue,
					percent,
					formatBytes(current*1024),
					formatBytes(total*1024),
					colorReset)
			}
		}
		fmt.Println() // New line after progress

		// Wait for completion
		if err := cmd.Wait(); err != nil {
			return "", fmt.Errorf("pg_basebackup failed: %w", err)
		}
	} else {
		// Run without progress monitoring
		output, err := cmd.CombinedOutput()
		if err != nil {
			return "", fmt.Errorf("pg_basebackup failed: %w\nOutput: %s", err, output)
		}
	}

	return backupPath, nil
}

func verifyBackup(config *Config, backupPath string) error {
	if config.DryRun {
		printMsg(colorYellow, "DRY RUN: Would verify backup")
		return nil
	}

	printMsg(colorBlue, "\nVerifying backup...")

	// Check if backup directory exists
	info, err := os.Stat(backupPath)
	if err != nil {
		return fmt.Errorf("backup directory not found: %w", err)
	}

	if !info.IsDir() {
		return fmt.Errorf("backup path is not a directory")
	}

	// For tar format, check for expected files
	if config.Format == "tar" {
		expectedFiles := []string{"base.tar.gz", "pg_wal.tar.gz"}
		if config.Compress == 0 {
			expectedFiles = []string{"base.tar", "pg_wal.tar"}
		}

		for _, file := range expectedFiles {
			path := filepath.Join(backupPath, file)
			if _, err := os.Stat(path); err != nil {
				return fmt.Errorf("expected file not found: %s", file)
			}
		}
	}

	// Calculate backup size
	var totalSize int64
	err = filepath.Walk(backupPath, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		if !info.IsDir() {
			totalSize += info.Size()
		}
		return nil
	})

	if err != nil {
		return fmt.Errorf("failed to calculate backup size: %w", err)
	}

	printMsg(colorGreen, fmt.Sprintf("✓ Backup verified, size: %s", formatBytes(totalSize)))

	return nil
}

func formatBytes(bytes int64) string {
	const unit = 1024
	if bytes < unit {
		return fmt.Sprintf("%d B", bytes)
	}
	div, exp := int64(unit), 0
	for n := bytes / unit; n >= unit; n /= unit {
		div *= unit
		exp++
	}
	return fmt.Sprintf("%.1f %ciB", float64(bytes)/float64(div), "KMGTPE"[exp])
}

func printMsg(color, msg string) {
	if color != "" {
		fmt.Printf("%s%s%s\n", color, msg, colorReset)
	} else {
		fmt.Println(msg)
	}
}

func getEnv(key, defaultVal string) string {
	if val := os.Getenv(key); val != "" {
		return val
	}
	return defaultVal
}

func getEnvInt(key string, defaultVal int) int {
	if val := os.Getenv(key); val != "" {
		if i, err := strconv.Atoi(val); err == nil {
			return i
		}
	}
	return defaultVal
}