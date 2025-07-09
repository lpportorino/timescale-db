# 🚀 TimescaleDB Tools - Junior Developer Evaluation Task

> **Welcome!** This project contains a coding challenge designed to evaluate your skills with Go, TimescaleDB, and Docker. You'll build a real-world tool while learning about time-series databases.

## 📚 Table of Contents

- [What You'll Learn](#-what-youll-learn)
- [Prerequisites](#-prerequisites)
- [Quick Start (5 minutes!)](#-quick-start-5-minutes)
- [Project Overview](#-project-overview)
- [Learning Resources](#-learning-resources)
- [Need Help?](#-need-help)

## 🎯 What This Evaluation Covers

This project will test your skills in:

1. **Go Programming** - Building command-line applications
2. **TimescaleDB** - Working with time-series data
3. **Docker** - Containerizing applications
4. **Problem Solving** - Understanding requirements and implementing solutions
5. **Code Quality** - Writing clean, maintainable code

## 📋 Prerequisites

Don't worry if you're new! Here's what you need:

### Required Software

1. **Docker** (for running containers)
   ```bash
   # Check if you have Docker:
   docker --version
   
   # If not, install from: https://docs.docker.com/get-docker/
   ```

2. **Make** (for running commands)
   ```bash
   # Check if you have Make:
   make --version
   
   # If not, install:
   # Ubuntu/Debian: sudo apt install make
   # Mac: brew install make
   # Windows: Use WSL2 or Git Bash
   ```

3. **Git** (for version control)
   ```bash
   # Check if you have Git:
   git --version
   
   # If not, install from: https://git-scm.com/downloads
   ```

### ⚠️ Important Setup Step

**Add this line to your `/etc/hosts` file:**
```bash
127.0.0.1    sych.local
```

This makes `sych.local` point to your local machine. Here's how:

```bash
# Linux/Mac:
echo "127.0.0.1    sych.local" | sudo tee -a /etc/hosts

# Windows (run as Administrator):
# Add the line to C:\Windows\System32\drivers\etc\hosts
```

### Optional (but helpful!)

- **Go** (only if you want to modify the code)
  - Install from: https://go.dev/dl/
  - Version 1.22 or higher

## 🏃 Quick Start (5 minutes!)

Let's see something working right away! Copy and paste these commands:

```bash
# 1. Clone this project
git clone <your-repository-url>
cd task

# 2. Start the database
cd db
make start

# 3. Load sample data (this has temperature readings!)
make restore BACKUP_DIR=backups/cluster_backup_20250704_165326

# 4. See the data!
cd ../example-app
make run
```

You should see:
- 🌡️ Temperature readings from weather stations
- 💚 Health metrics from services
- 📊 Real time-series data!

## 🗂️ Project Overview

Here's what each folder does:

```
timescaledb-tools/
│
├── 📁 db/                    # Database management
│   ├── 🔍 explore/          # See what's in your database
│   ├── 💾 save-restore/     # Backup and restore tools
│   └── 📊 backups/          # Sample data lives here!
│
├── 📁 example-app/          # Learn how to query time-series data
│
├── 📁 chart-generator/      # Create HTML charts from your data!
│
└── 📁 docs/                 # All the learning materials!
    ├── QUICKSTART.md       # Start here! (5 minutes)
    ├── LEARN_GO.md         # Go programming basics
    ├── DOCKER_BASICS.md    # Docker explained simply
    └── TIMESCALEDB_INTRO.md # Time-series databases 101
```

## 📖 Learning Path

### 🥇 Complete Beginner? Start Here:

1. **[QUICKSTART.md](docs/QUICKSTART.md)** - Get something working in 5 minutes
2. **[DOCKER_BASICS.md](docs/DOCKER_BASICS.md)** - Understand containers (30 min)
3. **[TIMESCALEDB_INTRO.md](docs/TIMESCALEDB_INTRO.md)** - What are time-series databases? (20 min)
4. **[LEARN_GO.md](docs/LEARN_GO.md)** - Go programming basics with playground examples (45 min)

### 🥈 Ready to Code? Continue Here:

5. **Explore the Database** - See what data you have
   ```bash
   cd db
   make explore
   # Look in reports/ folder for the generated documentation!
   ```

6. **Modify the Example App** - Change queries, add features
   ```bash
   cd example-app
   # Edit main.go (it's well commented!)
   make run
   ```

7. **Create a Backup** - Learn data safety
   ```bash
   cd db
   make backup
   ```

## 🔗 Learning Resources

### Go Programming
- 🎮 **[Go Playground](https://go.dev/play/)** - Try Go in your browser!
- 📘 **[A Tour of Go](https://go.dev/tour/)** - Interactive Go tutorial
- 📺 **[Learn Go in 12 Minutes](https://www.youtube.com/watch?v=C8LgvuEBraI)** - Quick video intro
- 📖 **[Go by Example](https://gobyexample.com/)** - Learn by doing

### Docker
- 🐳 **[Docker Getting Started](https://docs.docker.com/get-started/)** - Official tutorial
- 🎮 **[Play with Docker](https://labs.play-with-docker.com/)** - Try Docker in browser
- 📺 **[Docker in 100 Seconds](https://www.youtube.com/watch?v=Gjnup-PuquQ)** - Quick overview

### TimescaleDB
- 📊 **[TimescaleDB Docs](https://docs.timescale.com/)** - Official documentation
- 🎓 **[TimescaleDB Tutorial](https://docs.timescale.com/getting-started/latest/)** - Step by step
- 📺 **[What is Time-Series Data?](https://www.youtube.com/watch?v=Se5ipte9DMY)** - Video explanation

### PostgreSQL (TimescaleDB is built on this)
- 🐘 **[PostgreSQL Tutorial](https://www.postgresqltutorial.com/)** - SQL basics
- 🎮 **[PostgreSQL Playground](https://www.db-fiddle.com/)** - Try SQL online

## 🛠️ Common Tasks

### See What's in the Database

```bash
cd db
make explore
# Open reports/timescaledb_schema.html in your browser!
```

### Run Example Queries

```bash
cd example-app
make run
```

### Generate Charts

```bash
cd chart-generator
make run ARGS="--metric temperature --window 24h"
# Open chart.html in your browser!
```

### Create a Backup

```bash
cd db
make backup
# Your backup will be in backups/ with a timestamp
```

### Restore from Backup

```bash
cd db
make restore BACKUP_DIR=backups/your_backup_folder
```

## 🚨 Need Help?

### Quick Fixes

1. **"Cannot connect to Docker"**
   ```bash
   # Add yourself to docker group
   sudo usermod -aG docker $USER
   # Then logout and login again
   ```

2. **"Database not running"**
   ```bash
   cd db
   make status  # Check if running
   make start   # Start it
   ```

3. **"No data showing"**
   - Remember: The sample data is from July 2025!
   - The example app queries specific dates
   - Check [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for more

### Getting More Help

- 📖 Check **[TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** for common issues
- 💬 Ask questions in the issues section
- 🤝 Remember: Everyone was a beginner once!

## 🎯 Your Evaluation Task

### The Challenge: Build a Chart Generator

Navigate to the `chart-generator` directory to find your task. You'll build a command-line tool that:
- Connects to TimescaleDB
- Queries time-series data
- Generates beautiful HTML charts

```bash
cd chart-generator
cat README.md  # Read the full task requirements
```

This task will demonstrate your ability to:
- Work with databases and time-series data
- Build command-line tools in Go
- Use Docker for containerization
- Write clean, well-documented code

### Time Expectation

This task should take approximately 7 days to complete, depending on your experience level.

## 🌟 Tips for Success

1. **Don't Rush** - Take time to understand each part
2. **Experiment** - Change things and see what happens
3. **Read Errors** - They often tell you exactly what's wrong
4. **Use the Playground** - Try Go code in the browser first
5. **Ask Questions** - No question is too simple!

---

**Remember:** Every expert was once a beginner. You've got this! 🚀

*P.S. If you get stuck, that's normal! Check the [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) file or open an issue. We're here to help!*
