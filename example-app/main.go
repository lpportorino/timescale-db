package main

import (
	"database/sql"
	"fmt"
	"log"
	"os"
	"time"

	_ "github.com/lib/pq"
)

type DBConfig struct {
	Host     string
	Port     string
	User     string
	Password string
	Database string
}

func main() {
	config := getDBConfig()

	fmt.Println("Connecting to TimescaleDB...")
	db, err := connectToDB(config)
	if err != nil {
		log.Fatal("Failed to connect:", err)
	}
	defer db.Close()
	fmt.Println("Connected successfully!")

	// Example 1: Query temperature data
	fmt.Println("\n=== Temperature Data (2025-07-04) ===")
	if err := queryTemperatureData(db); err != nil {
		log.Printf("Error querying temperature data: %v", err)
	}

	// Example 2: Query health metrics
	fmt.Println("\n=== Health Metrics (2025-07-04) ===")
	if err := queryHealthMetrics(db); err != nil {
		log.Printf("Error querying health metrics: %v", err)
	}

	fmt.Println("\nConnection closed.")
}

func getDBConfig() DBConfig {
	return DBConfig{
		Host:     getEnv("PGHOST", "sych.local"),
		Port:     getEnv("PGPORT", "8094"),
		User:     getEnv("PGUSER", "jettison"),
		Password: getEnv("PGPASSWORD", "aMvzpGPgNVtH53S"),
		Database: getEnv("PGDATABASE", "jettison"),
	}
}

func connectToDB(config DBConfig) (*sql.DB, error) {
	connStr := fmt.Sprintf("host=%s port=%s user=%s password=%s dbname=%s sslmode=disable",
		config.Host, config.Port, config.User, config.Password, config.Database)

	db, err := sql.Open("postgres", connStr)
	if err != nil {
		return nil, err
	}

	// Test connection
	if err := db.Ping(); err != nil {
		db.Close()
		return nil, err
	}

	return db, nil
}

func queryTemperatureData(db *sql.DB) error {
	query := `
		SELECT time, station, temperature, humidity
		FROM meteo_metrics
		WHERE time >= '2025-07-04 00:00:00' AND time <= '2025-07-04 01:00:00'
		ORDER BY time DESC
		LIMIT 100
	`

	rows, err := db.Query(query)
	if err != nil {
		return err
	}
	defer rows.Close()

	count := 0
	var readings []struct {
		timestamp   time.Time
		station     string
		temperature float64
		humidity    float64
	}

	for rows.Next() {
		var r struct {
			timestamp   time.Time
			station     string
			temperature float64
			humidity    float64
		}

		if err := rows.Scan(&r.timestamp, &r.station, &r.temperature, &r.humidity); err != nil {
			return err
		}

		count++
		if len(readings) < 5 {
			readings = append(readings, r)
		}
	}

	if count > 0 {
		fmt.Printf("Found %d temperature readings\n\nFirst 5 readings:\n", count)
		for _, r := range readings {
			fmt.Printf("%s | %-12s | %6.2f°C | %5.2f%%\n",
				r.timestamp.Format("2006-01-02 15:04:05+00:00"),
				r.station, r.temperature, r.humidity)
		}
	} else {
		fmt.Println("No temperature data found in the specified time range")
	}

	return rows.Err()
}

func queryHealthMetrics(db *sql.DB) error {
	query := `
		SELECT 
			time,
			service,
			category,
			avg_health,
			min_percentage,
			max_percentage
		FROM health_metrics_1min_cagg
		WHERE time >= '2025-07-04 12:00:00' AND time <= '2025-07-04 13:00:00'
		ORDER BY time DESC, service, category
		LIMIT 100
	`

	rows, err := db.Query(query)
	if err != nil {
		return err
	}
	defer rows.Close()

	count := 0
	var metrics []struct {
		timestamp time.Time
		service   string
		category  string
		avgHealth float64
		minPct    float64
		maxPct    float64
	}

	for rows.Next() {
		var m struct {
			timestamp time.Time
			service   string
			category  string
			avgHealth float64
			minPct    float64
			maxPct    float64
		}

		if err := rows.Scan(&m.timestamp, &m.service, &m.category, &m.avgHealth, &m.minPct, &m.maxPct); err != nil {
			return err
		}

		count++
		if len(metrics) < 5 {
			metrics = append(metrics, m)
		}
	}

	if count > 0 {
		fmt.Printf("Found %d health metric entries\n\nFirst 5 entries:\n", count)
		for _, m := range metrics {
			// Truncate service name if too long
			displayService := m.service
			if len(displayService) > 30 {
				displayService = displayService[:30]
			}

			fmt.Printf("%s | %-30s | %-10s | Health: %6.2f | Min%%: %5.2f | Max%%: %5.2f\n",
				m.timestamp.Format("2006-01-02 15:04:05+00:00"),
				displayService, m.category, m.avgHealth, m.minPct, m.maxPct)
		}
	} else {
		fmt.Println("No health data found in the specified time range")
	}

	return rows.Err()
}

func getEnv(key, defaultVal string) string {
	if val := os.Getenv(key); val != "" {
		return val
	}
	return defaultVal
}
