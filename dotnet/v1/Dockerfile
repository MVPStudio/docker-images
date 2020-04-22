FROM mvpstudio/base:v1 AS base
ENV ASPNETCORE_URLS=http://*:8080

WORKDIR /home/mvp/app
EXPOSE 8080

# https://docs.microsoft.com/en-us/dotnet/core/install/linux-package-manager-debian10
RUN apt-get install wget && \
    wget -O- https://packages.microsoft.com/keys/microsoft.asc | \
    gpg --dearmor > microsoft.asc.gpg && \
    mv microsoft.asc.gpg /etc/apt/trusted.gpg.d/ && \
    wget https://packages.microsoft.com/config/debian/10/prod.list && \
    mv prod.list /etc/apt/sources.list.d/microsoft-prod.list && \
    apt-get update && apt-get install -y dotnet-runtime-3.1 && \
    apt-get install aspnetcore-runtime-3.1
