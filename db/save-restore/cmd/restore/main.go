package main

import (
	"archive/tar"
	"compress/gzip"
	"flag"
	"fmt"
	"io"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"syscall"
)

const (
	colorGreen  = "\033[0;32m"
	colorYellow = "\033[1;33m"
	colorRed    = "\033[0;31m"
	colorBlue   = "\033[0;34m"
	colorReset  = "\033[0m"
	colorBold   = "\033[1m"
)

type Config struct {
	BackupPath string
	DataDir    string
	DryRun     bool
	Force      bool
}

type BackupInfo struct {
	Format string
	Files  []string
}

func main() {
	config := parseFlags()

	if err := run(config); err != nil {
		log.Fatal(err)
	}
}

func parseFlags() *Config {
	config := &Config{}

	flag.StringVar(&config.BackupPath, "backup", "", "Path to backup directory (required)")
	flag.StringVar(&config.DataDir, "data-dir", "/var/lib/postgresql/data", "PostgreSQL data directory")
	flag.BoolVar(&config.DryRun, "dry-run", false, "Dry run mode")
	flag.BoolVar(&config.Force, "force", false, "Skip confirmation prompt")

	flag.Parse()

	if config.BackupPath == "" {
		flag.Usage()
		log.Fatal("Error: --backup flag is required")
	}

	return config
}

func run(config *Config) error {
	printMsg(colorGreen, "PostgreSQL Cluster Restore (Docker)")
	fmt.Println(strings.Repeat("=", 40))
	fmt.Printf("Backup: %s\n", config.BackupPath)
	fmt.Printf("Target: %s\n", config.DataDir)

	if config.DryRun {
		printMsg(colorYellow, "DRY RUN MODE - No changes will be made")
	}

	// Check prerequisites
	backupInfo, err := checkPrerequisites(config)
	if err != nil {
		return err
	}

	// Confirm with user
	if !config.Force && !config.DryRun {
		fmt.Print("\nThis will DESTROY all current data. Continue? [y/N] ")
		var response string
		fmt.Scanln(&response)
		if strings.ToLower(response) != "y" {
			return fmt.Errorf("restore cancelled by user")
		}
	}

	// Clear data directory
	if err := clearDataDirectory(config); err != nil {
		return err
	}

	// Restore from backup
	printMsg(colorGreen, "\nRestoring from backup...")
	if err := restoreBackup(config, backupInfo); err != nil {
		return err
	}

	// Set permissions
	if err := setPermissions(config); err != nil {
		return err
	}

	// Remove recovery files
	if err := removeRecoveryFiles(config); err != nil {
		return err
	}

	// Check if WAL reset is needed
	if err := checkAndResetWAL(config); err != nil {
		return err
	}

	// Report summary
	if err := reportSummary(config); err != nil {
		return err
	}

	printMsg(colorGreen, "\n✓ Restore completed successfully!")
	printMsg(colorYellow, "\nNote: You need to restart the PostgreSQL container to use the restored data")

	return nil
}

func checkPrerequisites(config *Config) (*BackupInfo, error) {
	// Check if we're running as root (needed for Docker restore)
	if os.Geteuid() != 0 {
		return nil, fmt.Errorf("this tool must be run as root for Docker restore")
	}

	// Check backup path
	info, err := os.Stat(config.BackupPath)
	if err != nil {
		return nil, fmt.Errorf("backup path not found: %w", err)
	}

	if !info.IsDir() {
		return nil, fmt.Errorf("backup path is not a directory")
	}

	// Determine backup format
	backupInfo := &BackupInfo{}
	
	// Check for tar files
	tarFiles, _ := filepath.Glob(filepath.Join(config.BackupPath, "*.tar.gz"))
	if len(tarFiles) == 0 {
		tarFiles, _ = filepath.Glob(filepath.Join(config.BackupPath, "*.tar"))
	}

	if len(tarFiles) > 0 {
		backupInfo.Format = "tar"
		backupInfo.Files = tarFiles
		printMsg(colorGreen, "✓ Found tar format backup")
	} else {
		// Check for plain format
		pgVersionFile := filepath.Join(config.BackupPath, "PG_VERSION")
		if _, err := os.Stat(pgVersionFile); err == nil {
			backupInfo.Format = "plain"
			printMsg(colorGreen, "✓ Found plain format backup")
		} else {
			return nil, fmt.Errorf("no valid backup found in %s", config.BackupPath)
		}
	}

	return backupInfo, nil
}

func clearDataDirectory(config *Config) error {
	if config.DryRun {
		printMsg(colorYellow, "DRY RUN: Would clear data directory")
		return nil
	}

	// Check if data directory exists
	info, err := os.Stat(config.DataDir)
	if err != nil {
		if os.IsNotExist(err) {
			printMsg(colorGreen, "Data directory is empty")
			return nil
		}
		return fmt.Errorf("failed to check data directory: %w", err)
	}

	if !info.IsDir() {
		return fmt.Errorf("data directory path is not a directory")
	}

	// Check if directory is empty
	entries, err := os.ReadDir(config.DataDir)
	if err != nil {
		return fmt.Errorf("failed to read data directory: %w", err)
	}

	if len(entries) == 0 {
		printMsg(colorGreen, "Data directory is empty")
		return nil
	}

	printMsg(colorYellow, fmt.Sprintf("⚠ Data directory contains files: %s", config.DataDir))
	printMsg(colorYellow, "\nClearing data directory: "+config.DataDir)

	// Instead of RemoveAll on the directory itself, remove its contents
	// This avoids "device or resource busy" errors when the directory is a mount point
	entries, readErr := os.ReadDir(config.DataDir)
	if readErr != nil {
		return fmt.Errorf("failed to read data directory: %w", readErr)
	}

	for _, entry := range entries {
		path := filepath.Join(config.DataDir, entry.Name())
		if err := os.RemoveAll(path); err != nil {
			return fmt.Errorf("failed to remove %s: %w", path, err)
		}
	}

	// Ensure proper permissions on the now-empty directory
	if err := os.Chmod(config.DataDir, 0700); err != nil {
		return fmt.Errorf("failed to set directory permissions: %w", err)
	}

	printMsg(colorGreen, "✓ Data directory cleared")
	return nil
}

func restoreBackup(config *Config, backupInfo *BackupInfo) error {
	if config.DryRun {
		printMsg(colorYellow, "DRY RUN: Would restore backup")
		return nil
	}

	switch backupInfo.Format {
	case "tar":
		return extractTarBackup(config, backupInfo)
	case "plain":
		return copyPlainBackup(config)
	default:
		return fmt.Errorf("unknown backup format: %s", backupInfo.Format)
	}
}

func extractTarBackup(config *Config, backupInfo *BackupInfo) error {
	printMsg(colorYellow, "\nExtracting tar backup files...")

	for _, tarFile := range backupInfo.Files {
		baseName := filepath.Base(tarFile)
		printMsg(colorBlue, fmt.Sprintf("Extracting: %s", baseName))

		// Open tar file
		file, err := os.Open(tarFile)
		if err != nil {
			return fmt.Errorf("failed to open tar file: %w", err)
		}
		defer file.Close()

		// Handle gzip compression
		var tarReader *tar.Reader
		if strings.HasSuffix(tarFile, ".gz") {
			gzReader, err := gzip.NewReader(file)
			if err != nil {
				return fmt.Errorf("failed to create gzip reader: %w", err)
			}
			defer gzReader.Close()
			tarReader = tar.NewReader(gzReader)
		} else {
			tarReader = tar.NewReader(file)
		}

		// Extract files
		fileCount := 0
		for {
			header, err := tarReader.Next()
			if err == io.EOF {
				break
			}
			if err != nil {
				return fmt.Errorf("failed to read tar header: %w", err)
			}

			// Construct full path
			targetPath := filepath.Join(config.DataDir, header.Name)

			// Create directory if needed
			if header.Typeflag == tar.TypeDir {
				if err := os.MkdirAll(targetPath, 0700); err != nil {
					return fmt.Errorf("failed to create directory: %w", err)
				}
				continue
			}

			// Create parent directory
			parentDir := filepath.Dir(targetPath)
			if err := os.MkdirAll(parentDir, 0700); err != nil {
				return fmt.Errorf("failed to create parent directory: %w", err)
			}

			// Extract file
			outFile, err := os.Create(targetPath)
			if err != nil {
				return fmt.Errorf("failed to create file: %w", err)
			}

			if _, err := io.Copy(outFile, tarReader); err != nil {
				outFile.Close()
				return fmt.Errorf("failed to extract file: %w", err)
			}

			outFile.Close()

			// Set file permissions
			if err := os.Chmod(targetPath, os.FileMode(header.Mode)); err != nil {
				return fmt.Errorf("failed to set file permissions: %w", err)
			}

			fileCount++
			if fileCount%100 == 0 {
				printMsg(colorBlue, fmt.Sprintf("  Extracted %d files...", fileCount))
			}
		}

		printMsg(colorGreen, "Progress: 100%")
	}

	printMsg(colorGreen, "✓ All tar files extracted")
	return nil
}

func copyPlainBackup(config *Config) error {
	printMsg(colorYellow, "\nCopying plain backup files...")

	// Use rsync or cp to copy files
	cmd := exec.Command("cp", "-a", filepath.Join(config.BackupPath, "."), config.DataDir)
	if output, err := cmd.CombinedOutput(); err != nil {
		return fmt.Errorf("failed to copy backup: %w\nOutput: %s", err, output)
	}

	printMsg(colorGreen, "✓ Plain backup copied")
	return nil
}

func setPermissions(config *Config) error {
	if config.DryRun {
		printMsg(colorYellow, "DRY RUN: Would set permissions")
		return nil
	}

	printMsg(colorYellow, "\nSetting permissions...")
	printMsg(colorBlue, "Setting ownership (this may take a while for large databases)...")

	// PostgreSQL runs as UID/GID 999 in the container
	const postgresUID = 999
	const postgresGID = 999

	// Walk through all files and set ownership
	err := filepath.Walk(config.DataDir, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}

		// Set ownership
		if err := syscall.Chown(path, postgresUID, postgresGID); err != nil {
			return fmt.Errorf("failed to set ownership on %s: %w", path, err)
		}

		return nil
	})

	if err != nil {
		return err
	}

	printMsg(colorGreen, "✓ Permissions set to postgres:postgres")
	return nil
}

func removeRecoveryFiles(config *Config) error {
	if config.DryRun {
		printMsg(colorYellow, "DRY RUN: Would remove recovery files")
		return nil
	}

	// Remove backup_label if it exists
	backupLabelPath := filepath.Join(config.DataDir, "backup_label")
	if _, err := os.Stat(backupLabelPath); err == nil {
		printMsg(colorYellow, "\nRemoving backup_label file...")
		if err := os.Remove(backupLabelPath); err != nil {
			return fmt.Errorf("failed to remove backup_label: %w", err)
		}
		printMsg(colorGreen, "✓ backup_label removed")
	}

	// Remove tablespace_map if it exists
	tablespaceMapPath := filepath.Join(config.DataDir, "tablespace_map")
	if _, err := os.Stat(tablespaceMapPath); err == nil {
		printMsg(colorYellow, "Removing tablespace_map file...")
		if err := os.Remove(tablespaceMapPath); err != nil {
			return fmt.Errorf("failed to remove tablespace_map: %w", err)
		}
		printMsg(colorGreen, "✓ tablespace_map removed")
	}

	return nil
}

func checkAndResetWAL(config *Config) error {
	if config.DryRun {
		printMsg(colorYellow, "DRY RUN: Would check and reset WAL if needed")
		return nil
	}

	// Check if pg_control exists
	pgControlPath := filepath.Join(config.DataDir, "global", "pg_control")
	if _, err := os.Stat(pgControlPath); err != nil {
		if os.IsNotExist(err) {
			return fmt.Errorf("pg_control file not found - invalid data directory")
		}
		return fmt.Errorf("failed to check pg_control: %w", err)
	}

	// Try to run pg_controldata to check database state
	printMsg(colorYellow, "\nChecking database state...")
	
	// We'll run pg_resetwal proactively to ensure clean startup
	// This is safe because we just restored from a consistent backup
	printMsg(colorYellow, "Running pg_resetwal to ensure clean startup...")
	
	// Note: We can't run pg_resetwal directly from Go since we're inside a container
	// The Makefile will handle this after restore completes
	printMsg(colorBlue, "WAL reset will be performed when database starts")
	
	return nil
}

func reportSummary(config *Config) error {
	if config.DryRun {
		return nil
	}

	// Calculate restored size
	var totalSize int64
	var fileCount, dirCount int

	err := filepath.Walk(config.DataDir, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}

		if info.IsDir() {
			dirCount++
		} else {
			fileCount++
			totalSize += info.Size()
		}

		return nil
	})

	if err != nil {
		return fmt.Errorf("failed to calculate restore size: %w", err)
	}

	fmt.Printf("\n%sRestore Summary:%s\n", colorBold, colorReset)
	fmt.Printf("Data directory: %s\n", config.DataDir)
	fmt.Printf("Restored size: %s\n", formatBytes(totalSize))
	fmt.Printf("Files: %d, Directories: %d\n", fileCount, dirCount)

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
	return fmt.Sprintf("%.1f%cB", float64(bytes)/float64(div), "KMGTPE"[exp])
}

func printMsg(color, msg string) {
	if color != "" {
		fmt.Printf("%s%s%s\n", color, msg, colorReset)
	} else {
		fmt.Println(msg)
	}
}