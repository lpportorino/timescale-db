# 🐳 Docker Basics - Containers Made Simple!

> **Never used Docker?** No problem! Think of Docker as a way to package your app with everything it needs to run, like a lunchbox with your meal inside!

## 📚 Table of Contents

1. [What is Docker?](#-what-is-docker)
2. [Key Concepts Explained](#-key-concepts-explained)
3. [Essential Docker Commands](#-essential-docker-commands)
4. [Understanding Our Project's Docker Usage](#-understanding-our-projects-docker-usage)
5. [Hands-On Exercises](#-hands-on-exercises)
6. [Common Problems & Solutions](#-common-problems--solutions)

## 🤔 What is Docker?

Imagine you're moving to a new house. You could:
- 🚚 **Option 1**: Throw everything loosely in a truck (messy, things might break)
- 📦 **Option 2**: Pack everything in labeled boxes (organized, safe, easy to unpack)

Docker is like Option 2 for software! It packages your application and everything it needs into a "container".

### Why Use Docker?

1. **Works Everywhere** - If it runs on your laptop, it'll run on any server
2. **No More "Works on My Machine"** - Everyone gets the same environment
3. **Easy to Share** - Send your whole app setup to a friend with one command
4. **Clean** - Delete a container, and it's gone completely

## 🎯 Key Concepts Explained

### 1. Image vs Container

Think of it like this:
- **Image** = Recipe 📜 (instructions)
- **Container** = The actual cake 🎂 (running instance)

```bash
# Pull an image (download the recipe)
docker pull nginx

# Run a container (bake the cake)
docker run nginx
```

### 2. Dockerfile

A Dockerfile is like a recipe card that tells Docker how to build your image.

```dockerfile
# Start with a base (like "preheat oven to 350°F")
FROM ubuntu:22.04

# Run commands (like "mix ingredients")
RUN apt-get update && apt-get install -y python3

# Copy your code (like "pour into pan")
COPY myapp.py /app/

# Set the startup command (like "bake for 30 minutes")
CMD ["python3", "/app/myapp.py"]
```

### 3. Volumes

Volumes are like external hard drives for your containers. They let data persist even when the container stops.

```bash
# Without volume: data disappears when container stops
docker run postgres

# With volume: data stays safe
docker run -v mydata:/var/lib/postgresql/data postgres
```

## 🛠️ Essential Docker Commands

### The Basics

```bash
# See what's running
docker ps

# See ALL containers (including stopped ones)
docker ps -a

# Stop a container
docker stop container_name

# Remove a container
docker rm container_name

# See all images
docker images

# Remove an image
docker rmi image_name
```

### 🎮 Try It Yourself!

Let's run a simple web server:

```bash
# 1. Run nginx web server
docker run -d -p 8080:80 --name myweb nginx

# What this means:
# -d = Run in background (detached)
# -p 8080:80 = Forward port 8080 on your computer to port 80 in container
# --name myweb = Give it a friendly name
# nginx = The image to use

# 2. Visit http://localhost:8080 in your browser!

# 3. See the logs
docker logs myweb

# 4. Stop it
docker stop myweb

# 5. Remove it
docker rm myweb
```

## 🔍 Understanding Our Project's Docker Usage

Let's decode our project's Docker commands!

### 1. Our Database Container

When you run `make start` in the `db` folder, it does this:

```bash
docker run -d \
    --name timescaledb-local \
    --network host \
    -e POSTGRES_PASSWORD=secretpass \
    -v $(PWD)/mnt/db/postgres:/var/lib/postgresql/data \
    timescale/timescaledb:latest-pg17
```

**What each part means:**
- `docker run -d` = Start a new container in background
- `--name timescaledb-local` = Call it "timescaledb-local"
- `--network host` = Use your computer's network directly
- `-e POSTGRES_PASSWORD=secretpass` = Set an environment variable
- `-v $(PWD)/mnt/db/postgres:/var/lib/postgresql/data` = Save data outside container
- `timescale/timescaledb:latest-pg17` = Use TimescaleDB image

### 2. Our Go Application Dockerfile

Here's a simplified version of our app's Dockerfile:

```dockerfile
# Build stage - compile our Go code
FROM golang:1.22-alpine AS builder
WORKDIR /build
COPY . .
RUN go build -o myapp

# Run stage - smaller image for running
FROM alpine:3.19
COPY --from=builder /build/myapp /usr/local/bin/
CMD ["myapp"]
```

**Multi-stage build benefits:**
- First stage: Has Go compiler (big image ~300MB)
- Second stage: Just needs to run the app (small image ~10MB)
- Result: Tiny final image!

## 🎯 Hands-On Exercises

### Exercise 1: Hello World Container

Create a file named `Dockerfile`:

```dockerfile
FROM alpine:3.19
CMD ["echo", "Hello from Docker! 🐳"]
```

Build and run it:

```bash
# Build the image
docker build -t myhello .

# Run it
docker run myhello
```

### Exercise 2: Interactive Container

Let's explore inside a container:

```bash
# Start an Ubuntu container interactively
docker run -it ubuntu:22.04 /bin/bash

# Now you're INSIDE the container! Try:
ls /
whoami
echo "I'm in a container!"

# Exit the container
exit
```

### Exercise 3: Web Server with Custom Page

1. Create `index.html`:
```html
<!DOCTYPE html>
<html>
<body>
    <h1>My Docker Web Server! 🚀</h1>
    <p>If you see this, Docker is working!</p>
</body>
</html>
```

2. Create `Dockerfile`:
```dockerfile
FROM nginx:alpine
COPY index.html /usr/share/nginx/html/
```

3. Build and run:
```bash
docker build -t myweb .
docker run -d -p 8080:80 myweb
# Visit http://localhost:8080
```

## 🚨 Common Problems & Solutions

### 1. "Cannot connect to Docker daemon"

**Problem**: Docker isn't running or you don't have permission

**Solution**:
```bash
# Check if Docker is running
docker --version

# On Linux, add yourself to docker group
sudo usermod -aG docker $USER
# Then logout and login again

# On Mac/Windows: Make sure Docker Desktop is running
```

### 2. "Port already in use"

**Problem**: Something else is using that port

**Solution**:
```bash
# Find what's using port 8080
# Linux/Mac:
lsof -i :8080
# Windows:
netstat -ano | findstr :8080

# Or just use a different port:
docker run -p 8081:80 nginx  # Use 8081 instead
```

### 3. "No space left on device"

**Problem**: Docker images/containers taking too much space

**Solution**:
```bash
# See Docker disk usage
docker system df

# Clean up everything not in use
docker system prune -a

# Remove specific images
docker images
docker rmi image_name
```

### 4. Container Stops Immediately

**Problem**: The main process ended

**Solution**: Check logs!
```bash
docker logs container_name

# Run interactively to debug
docker run -it image_name /bin/sh
```

## 📚 Docker Compose (Bonus!)

Docker Compose lets you define multiple containers in one file. Here's a simple example:

`docker-compose.yml`:
```yaml
version: '3'
services:
  web:
    image: nginx
    ports:
      - "8080:80"
  
  database:
    image: postgres
    environment:
      POSTGRES_PASSWORD: secret
    volumes:
      - dbdata:/var/lib/postgresql/data

volumes:
  dbdata:
```

Run it all with:
```bash
docker-compose up
```

## 🎓 Learning Resources

### Interactive Learning
- 🎮 **[Play with Docker](https://labs.play-with-docker.com/)** - Free Docker playground in browser
- 🎮 **[Docker Tutorial](https://www.docker.com/101-tutorial/)** - Official interactive tutorial

### Videos
- 📺 **[Docker in 100 Seconds](https://www.youtube.com/watch?v=Gjnup-PuquQ)**
- 📺 **[Docker Tutorial for Beginners](https://www.youtube.com/watch?v=fqMOX6JJhGo)** - FreeCodeCamp
- 📺 **[You Need to Learn Docker RIGHT NOW!!](https://www.youtube.com/watch?v=eGz9DS-aIeY)** - NetworkChuck

### Documentation
- 📖 **[Docker Get Started](https://docs.docker.com/get-started/)** - Official guide
- 📖 **[Docker Cheat Sheet](https://github.com/wsargent/docker-cheat-sheet)** - Quick reference

## 🎯 Quick Reference Card

```bash
# Running Containers
docker run image_name              # Run container
docker run -d image_name          # Run in background
docker run -p 8080:80 image      # Map ports
docker run -v /host:/container    # Mount volume
docker run --name myapp image     # Name it

# Managing Containers
docker ps                         # List running
docker ps -a                      # List all
docker stop container             # Stop
docker start container            # Start
docker rm container               # Remove
docker logs container             # View logs
docker exec -it container bash    # Enter container

# Managing Images
docker images                     # List images
docker pull image:tag            # Download image
docker build -t name .           # Build image
docker rmi image                 # Remove image

# Cleanup
docker system prune              # Remove unused
docker system prune -a           # Remove all unused
```

## 💡 Pro Tips for Beginners

1. **Always name your containers** - Use `--name` for easier management
2. **Check logs when things go wrong** - `docker logs` is your friend
3. **Use official images** - They're well-maintained and documented
4. **Start simple** - Don't try to containerize everything at once
5. **Clean up regularly** - Docker can use lots of disk space

## 🏁 What's Next?

Now that you understand Docker:
1. Try the exercises above
2. Look at our project's Dockerfiles and understand them
3. Learn about [TimescaleDB](TIMESCALEDB_INTRO.md) - the database we're using
4. Try modifying our Dockerfiles to add new features

---

**Remember**: Docker might seem complex at first, but it's just a tool for packaging and running applications. Start with simple examples and build up! 🚀

*Questions? Check our [TROUBLESHOOTING.md](TROUBLESHOOTING.md) or ask in the issues!*