# Containerize a dotnet project

This is the incomplete beginning of a dotnet image created by following 
[Microsoft Docs](https://docs.microsoft.com/en-us/dotnet/core/install/linux-package-manager-debian10). 
Projects that use dotnet and ASP.net should use this image as their base.

This base image is available at mvpstudio/dotnet:<VERSION>. The Dockerfile is placed in the directory
 with the base image version designation.

As for which versions of dotnet runtime, aspnetcore runtime, and dotnet sdk are being used, take a look 
at the `Dockerfile` which versions inside one of the version directories. The v1 base image uses the 
3.1 dotnet and aspnetcore runtimes.

To create a complete a Dockerfile for individual projects, be sure to create a Dockerfile with 
content similar to what is shown below. Replace <VERSION> with the latest version, e.g. `v1`,
and all instances of `LittleHelpBook` with the appropriate project name. Once these replacements 
are made, the Dockerfile should be complete.

```Docker
FROM mvpstudio/dotnet:<VERSION> as base
FROM mcr.microsoft.com/dotnet/core/sdk:3.1-buster AS build
WORKDIR /src
COPY ["LittleHelpBook.csproj", ""]
RUN dotnet restore "./LittleHelpBook.csproj"
COPY . .
WORKDIR "/src/."
RUN dotnet build "LittleHelpBook.csproj" -c Release -o /app/build

FROM build AS publish
RUN dotnet publish "LittleHelpBook.csproj" -c Release -o /app/publish

FROM base AS final
USER mvp
WORKDIR /home/mvp/app
COPY --from=publish /app/publish .

ENTRYPOINT ["dotnet", "LittleHelpBook.dll"]
```
