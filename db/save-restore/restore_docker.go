package main

import (
	"fmt"
	"os"
	"os/exec"
)

// This is a wrapper that runs the restore command inside Docker with proper privileges
func main() {
	// Get backup path from args
	if len(os.Args) < 2 {
		fmt.Fprintf(os.Stderr, "Usage: %s <backup-path>\n", os.Args[0])
		os.Exit(1)
	}

	backupPath := os.Args[1]

	// Build Docker command
	args := []string{
		"run", "--rm",
		"--privileged",
		"-v", fmt.Sprintf("%s:/backup:ro", backupPath),
		"-v", "$(PWD)/mnt/db/postgres:/var/lib/postgresql/data",
		"timescaledb-save-restore",
		"restore",
		"--backup", "/backup",
	}

	// Execute Docker command
	cmd := exec.Command("docker", args...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	cmd.Stdin = os.Stdin

	if err := cmd.Run(); err != nil {
		os.Exit(1)
	}
}