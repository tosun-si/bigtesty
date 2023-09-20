FROM golang:1.20-alpine as builder

WORKDIR /app

COPY . .

RUN GOOS=linux GOARCH=amd64 go build -ldflags="-w -s" -o bin/bigtesty

FROM alpine:latest

WORKDIR /app

RUN apk add docker-cli curl

COPY --from=builder /app/bin/bigtesty .

ENTRYPOINT ["/app/bigtesty"]
