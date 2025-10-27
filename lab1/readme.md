# Lab 1 Report: HTTP Server and Client Implementation

## Directory

## Docker Compose Execution

The project can be deployed using Docker Compose with the following commands:

```bash
docker-compose build

docker-compose up

```

![alt text](images/image.png)
![alt text](images/image1.png)

docker desktop:
![alt text](images/image2.png)

## Implementation Details

The server demonstrates comprehensive functionality:

    Navigation through nested directory structures

    Bidirectional directory traversal (forward and backward)

    PDF file rendering capability

    PNG image display functionality

    HTML file processing

    Markdown and text file download support

The implementation satisfies all fundamental requirements for HTTP file serving operations.


## Client Application Usage

The client operates independently of the Docker Compose environment. Execution follows this pattern:

```bash
python client.py localhost 8080 <filename>
```
