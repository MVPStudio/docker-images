# MVP Studio Docker Images

This is the parent repo for all our Docker containers. We try to maintain a strict hierarchy for containers so that
everything has as its lowest layer our `base` image, and then, for example, all node.js projects have as their base the
`node` image, etc. The reason for this is it allows us to upgrade, patch vulnerabilities, etc. in a very easy consistent
way. For example, imaging there's a new vulnerability in zlib (a common compression library used by most HTTP servers).
That would likely affect a lot of MVP Studio projects.  If each project had their own base image we'd have to figure out
how to patch each individually. However, since all our images are based off `base` we can simply update that image and
then rebuild the rest. Similarly, if there was a vulnerability in node.js we could update just our `node` image and then
rebuild anything that's based off that.

# Layout

The `build-push.py` script in this repo lets us recursively build all our images in dependency order. That is, suppose
make a change to our base image and we want to rebuild it and everything that depends on it. To do that you'd just
change the base image and run `build-push.py` and it would automatically build all the other images. In order to do
that each image must have a special format in this directory:

+ <repo>/
  + Dockerfile.template
  + context/
    + <files that belong in the Docker context>

Note that `<repo>` is a directory name and it must match the "short name" of the Dockerhub repo whose image it builds.
By "short name" here we mean the name of the repo with the `mvpstudio/` prefix omitted.  That is, the directory that
builds `mvpstudio/base` must be called `base` and the directory that builds `mvpstudio/python` must be called `python`.

The Dockerfile.template is a [mustache template](http://mustache.github.io/) that expands to your `Dockerfile`. And the
context directory should contain the entire Docker context that should be used to build your image _except_ for the
`Dockerfile`.

The `Dockerfile.template` is a simple mustache template that will be called with a dictionary mapping the short repo
name name to the version of the image in that repo. For example, the `Dockerfile.template` for our Python
image looks like:

```
FROM mvpstudio/base:{{ base }}

RUN apt-get update -y && \
    apt-get install -y python3 python3-dev python3-pip
```

Note that's a regular `Dockerfile` except for the `{{ base }}` part - that will be expanded to match the `version`
specified in `base/container.yml`. We also rely on this format to determine dependencies between images. If the
`Dockefile.template` for image A refers to the version number for image B via a Mustache parameter (as the python image
example above refers to the `base` repo) then we say that A has a dependency on B so we'll build image B before we build
A and we'll inject the new version number for B into A's `Dockerfile`.

`build-push.py` then constructs a final Docker context under the `build` directory containing all the files in `context`
plus the expanded `Dockerfile.template` and it builds the image. Once it's built one image the others that depended upon
it can now be built, etc. and so eventually all the images will be built.

# Building

All the images in here are built automatically by CircleCI upon merge to `master`. The build is configured via the
`.circleci/config.yml` file here and the CircliCI build itself can be found in the [`docker-images`
project](https://app.circleci.com/pipelines/github/MVPStudio/docker-images) on CircleCI.

Note that in order to run `build-push.py` manually you should already be logged into Dockerhub; if you aren't run
`docker login`.  That script also has a few simple dependencies. To install them all run `pip install -r
requirements.txt`.

# Versioning

We do *not* use the common `latest` tag ever. That's because if you use `latest` it can be hard to know when the image
was last built so you don't know what software it contained.  Furthermore, if you use `latest` Kubernetes won't be able
to know when the image was updated so it won't pull new versions. Instead, we use explicit versioning like `v001`,
`v002`, etc. Version numbers are automatically determined by querying Dockerhub for the current version of an image and
then incrementing by 1.

# MVP User

It is generally considered [a bad idea](https://www.oreilly.com/ideas/five-security-concerns-when-using-docker) to run
apps in Docker containers as root. Thus we run all apps as the `mvp` user (which is created in our base image).

# App Location

For quick debugging it can be handy to know where the app is actually installed. By convention we always put the
application in `/home/mvp/app`. That is, the main executable and as much of the supporting code and configuration as
possible can all be found in that folder.
