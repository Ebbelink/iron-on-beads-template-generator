# Building and running the container locally
```
docker build . --progress=plain -t madailei/iron-on-beads-template-generator

docker container run -p 8000:8000 madailei/iron-on-beads-template-generator
```