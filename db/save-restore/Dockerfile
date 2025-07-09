# Build stage
FROM golang:1.22-alpine AS builder

# Install build dependencies
RUN apk add --no-cache git

WORKDIR /build

# Copy go mod files
COPY go.mod go.sum* ./
RUN go mod download

# Copy source code
COPY cmd/ ./cmd/

# Build both tools
RUN go build -o save ./cmd/save/main.go
RUN go build -o restore ./cmd/restore/main.go

# Runtime stage
FROM alpine:3.19

# Install PostgreSQL client tools from edge repository for version 17
RUN echo "http://dl-cdn.alpinelinux.org/alpine/edge/main" >> /etc/apk/repositories && \
    apk add --no-cache postgresql17-client

# Copy binaries from builder
COPY --from=builder /build/save /usr/local/bin/
COPY --from=builder /build/restore /usr/local/bin/

# Make them executable
RUN chmod +x /usr/local/bin/save /usr/local/bin/restore

# Create necessary directories
RUN mkdir -p /app/backups /mnt/db

WORKDIR /app

# Default to save command
CMD ["save"]