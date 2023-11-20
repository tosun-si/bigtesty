FROM golang:1.20-alpine as builder

WORKDIR /app

COPY . .

RUN GOOS=linux GOARCH=amd64 go build -ldflags="-w -s" -o bin/bigtestyapp

FROM mgoltzsche/podman:rootless

WORKDIR /app

RUN ln -s $(which podman) /usr/local/bin/docker

COPY . .

COPY --from=builder /app/bin/bigtestyapp .

ENTRYPOINT ["/app/bigtestyapp"]
