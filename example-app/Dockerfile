# Build stage
FROM golang:1.22-alpine AS builder

WORKDIR /build

# Copy go mod files
COPY go.mod go.sum* ./
RUN go mod download

# Copy source code
COPY main.go ./

# Build the application
RUN go build -o example-app main.go

# Runtime stage
FROM alpine:3.19

# Install ca-certificates for SSL
RUN apk add --no-cache ca-certificates

WORKDIR /app

# Copy binary from builder
COPY --from=builder /build/example-app .

CMD ["./example-app"]