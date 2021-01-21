# MVP Studio Docker Images

This is the parent repo for all our Docker containers. We try to maintain a strict hierarchy for containers so that
everything has as its lowest layer our `base` image, and then, for example, all node.js projects have as their base the
`node` image, etc. The reason for this is it allows us to upgrade, patch vulnerabilities, etc. in a very easy consistent
way. For example, imaging there's a new vulnerability in zlib (a common compression library used by most HTTP servers).
That would likely affect a lot of MVP Studio projects.  If each project had their own base image we'd have to figure out
how to patch each individually. However, since all our images are based off `base` we can simply update that image and
then rebuild the rest. Similarly, if there was a vulnerability in node.js we could update just our `node` image and then
rebuild anything that's based off that.

# Building

All the images in here are built automatically by CircleCI upon merge to `master`. The build is configured via the
`.circleci/config.yml` file here and the CircliCI build itself can be found in the [`docker-images`
project](https://app.circleci.com/pipelines/github/MVPStudio/docker-images) on CircleCI.

Currently the `.circleci/config.yml` file _explicitly lists the version tags_ for each image so if you modify an image
you must also modify that file. It also currently duplicates, via copy-and-past, the jobs. It is an open TODO to:

1. Make the versioning automatic (pull the current tags, increment the highest, and use that).
2. Use [CircleCI's reusable config](https://circleci.com/docs/2.0/reusing-config) tools so that everything isn't cut and
   paste.
3. Each run is currently a separate job so that it must duplicate the steps of pulling the previous images. It should
   instead be a series of steps in a single job so a container that depends on another doesn't have to pull the build
   for the previous one.
4. Turn the `Dockerfile`s into templates so that the proper tags for dependencies can be injected. That is, if `python`
   depends on `base` and we push a change to `base` we'd like the `FROM mvpstudio/base:<version>` line to have it's
   `<version>` replaced with the newly built version of base so it gets properly rebuilt.
5. Automatically infer the dependency graph from the `FROM` lines in the images so it doesn't have to be hard-coded.

Pull requests to tackle any of the above are welcome.

# Versioning

We do *not* use the common `latest` tag ever. That's because if you use `latest` it can be hard to know when the image
was last built so you don't know what software it contained. Instead, we use explicit versioning like `v1`, `v2`, etc.

# MVP User

It is generally considered [a bad idea](https://www.oreilly.com/ideas/five-security-concerns-when-using-docker) to run
apps in Docker containers as root. Thus we run all apps as the `mvp` user (which is created in our base image).

# App Location

For quick debugging it can be handy to know where the app is actually installed. By convention we always put the
application in `/home/mvp/app`. That is, the main executable and as much of the supporting code and configuration as
possible can all be found in that folder.
