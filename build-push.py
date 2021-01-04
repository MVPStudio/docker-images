import argparse
import chevron
import copy
import logging
import pathlib
import shutil
import subprocess
import sys
import requests
import re


THIS_DIR = pathlib.Path(__file__).parent
BUILD_DIR = THIS_DIR / 'build'


logging.basicConfig(level=logging.INFO, stream=sys.stderr)
log = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(
        description='Build and push all containers. See the README.')

    parser.add_argument('-p', '--no_push', action='store_true', default=False,
                        help='If given, build the containers but do not push them.')
    parser.add_argument('-o', '--only', action='append', type=str,
                        help='If given build only this container and the containers on which it depends (unless '
                        '--no_depends is given). The values passed should be repo names omitting the mvpstudio/ prefix '
                        '(e.g. like "base" to indicate mvpstudio/base). Can pass this argument more than once to build '
                        'more than one container.')
    args = parser.parse_args()
    return args


def get_max_version(repo):
    """Returns a list of the largest integer extracted from a tag in the format vX. Tags that don't match vX where X is
    an integer are ignored. If no matching tags are found a 0 is returned.

    Parameters
    ----------
    repo : str
        The short repo name; that is, the name omitting the `mvpstudio/` prefix.
    """
    # Note that the following is an undocumented dockerhub API. It appears to be the standard v2 API
    # (https://docs.docker.com/registry/spec/api/#listing-image-tags) given the `v2/` part of the URL but it isn't.
    # Dockerhub _does_ support the standard v2 API at:
    #
    # https://registry.hub.docker.com/v2/mvpstudio/%s/tags/list
    #
    # Note the missing `repositories/` and the additonal `list` in the URL. We don't use the V2 API however since that
    # requires authentication and all we need is the public tag data.
    tag_re = re.compile('^v(\d+)$')
    max_tag = 0
    page_size = 2
    next = 'https://registry.hub.docker.com/v2/repositories/mvpstudio/%s/tags?page_size=%s' % (repo, page_size)
    while True:
        result = requests.get(next)
        result.raise_for_status()
        result_json = result.json()
        for tag_data in result_json['results']:
            log.debug('Found tag: %s', tag_data['name'])
            m = tag_re.fullmatch(tag_data['name'])
            if m is not None:
                tag_version = int(m.group(1))
                max_tag = max(max_tag, tag_version)
            else:
                log.debug('Ignoring tag %s as it is not in vX format with X being an integer.', tag_data['name'])
        if result_json['next'] is None:
            break
        else:
            next = result_json['next']
    return max_tag


class ImageToBuild:
    """An image to be built."""
    def __init__(self, directory, version, deps):
        """Constructor.

        Parameters
        ----------
        directory : pathlib.Path
            Path to the directory holding the container.yml and Dockerfile.template files.

        version : int
            The version of the container to build and push.

        deps : list of str
            A list of other containers upon which this one depends. Should be just a short repo name (e.g.
            "base"). We'll figure out the version that corresponds to by pulling the repo data for the dependency from
            Dockerhub.
        """
        self.directory = directory
        self.version = version
        self.deps = deps

    @property
    def repo(self):
        """The "short" repo name - the repo without the 'mvpstudio/' prefix."""
        return self.directory.name

    @property
    def full_repo(self):
        """The full repo including the prefix."""
        return 'mvpstudio/%s' % self.repo

    @property
    def string_version(self):
        """The stringified version, with leading `v` and left-padded 0's."""
        return 'v%03d' % self.version


def build_one(to_build, built, push):
    """Sets up the context, filling in the template information from Dockerfile.template, and runs docker build.

    Parameters
    ----------
    to_build : ImageToBuild
        The image we should build.

    built : dict from str to ImageToBuild
        A dict mapping the repo name of an image to the ImageToBuild for that image. This dict contains only
        images that were already built.

    push : bool
        If true push the image after building it. If false, don't.
    """
    log.info('Building %s:%s', to_build.repo, to_build.string_version)
    build_dir = BUILD_DIR / to_build.directory
    if build_dir.exists():
        # Remove the build directory if it exists so we don't accidentally have some stale data in the docker context
        # from a previous build.
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True)
    context_dir = to_build.directory / 'context'
    if context_dir.exists():
        shutil.copytree(context_dir, build_dir)

    with open(to_build.directory / 'Dockerfile.template', 'r') as docker_template:
        template_data = {repo: img.string_version for repo, img in built.items()}
        rendered = chevron.render(docker_template, template_data)
    with open(build_dir / 'Dockerfile', 'w') as outf:
        outf.write(rendered)

    tag = '%s:%s' % (to_build.full_repo, to_build.string_version)
    subprocess.check_call(['docker', 'build', '-t', tag, str(build_dir)])

    if push:
        subprocess.check_call(['docker', 'push', tag])


def do_builds(to_build, push):
    """Build everything in topological order.

    Parameters
    ----------
    to_build : dict from str to ImageToBuild
        Map from repo name to the ImageToBuild for everything that is to be built.

    push : bool
        Indicates if we should push the images after building them or not.
    """
    # build up a map from repo name to the ImageToBuild for images that we're ready to build (all their dependencies
    # have been built).
    ready = {}
    for candidate in to_build.values():
        if len(candidate.deps) == 0:
            log.info('%s has no dependencies and can be built immediately', candidate.repo)
            ready[candidate.repo] = candidate
    for r in ready.keys():
        del to_build[r]

    built = {}
    while len(ready) > 0:
        next_build = next(iter(ready.values()))
        build_one(next_build, built, push)
        built[next_build.repo] = next_build
        del ready[next_build.repo]

        # The following is far less efficient than it might be but it shouldn't matter.
        for candidate in to_build.values():
            not_built_yet = [x for x in candidate.deps if x not in built]
            if len(not_built_yet) > 0:
                log.debug('%s is still not ready as %s have not been built yet', candidate.repo, not_built_yet)
            else:
                log.info('%s is now ready to be built.', candidate.repo)
                ready[candidate.repo] = candidate
        for r in ready.keys():
            del to_build[r]

    if len(to_build) != 0:
        log.error('Unable to build all containers.')
        log.error('The following were not built:')
        for r in to_build.keys():
            log.error('%s', r)
        sys.exit(1)


def main():
    args = parse_args()
    log.info('Looking for container to build under %s', THIS_DIR.resolve())
    # Build up a dict from repo to ImageToBuild.
    all_containers = {}
    for dockerfile_templ in THIS_DIR.glob('*/Dockerfile.template'):
        log.info('Parsing %s', dockerfile_templ)
        repo = dockerfile_templ.parent.name
        version = get_max_version(repo) + 1
        with open(dockerfile_templ, 'r') as tf:
            tokens = chevron.tokenizer.tokenize(tf)
            deps = [x[1] for x in tokens if x[0] == 'variable']
            log.info('Found repo %s with version %s and deps %s',
                     repo, version, deps)
            all_containers[repo] = ImageToBuild(
                directory=dockerfile_templ.parent,
                version=version,
                deps=deps)

    # to_build is like all_containers but contains only the images we actually want to build.
    to_build = {}
    if args.only is not None:
        only_set = set(args.only)
        to_build = {r: c for r, c in all_containers.items() if r in only_set}
    else:
        to_build = copy.copy(all_containers)

    do_builds(to_build, not args.no_push)


if __name__ == '__main__':
    main()
