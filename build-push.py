import argparse
import chevron
import copy
import logging
import pathlib
import shutil
import subprocess
import sys
import yaml


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
                        '--no_depends is given). The values passed should be repo names like "mvpstudio/base". Can '
                        'pass this argument more than once to build more than one container.')
    parser.add_argument('-n', '--no_depends', action='store_true', default=False,
                        help='Build only the images specified by --only and do not build the images upon which they '
                        'depend. This will therefore fail if the dependent images are not already built.')
    args = parser.parse_args()
    return args


class ImageToBuild:
    """An image to be built."""
    def __init__(self, repo, version, deps, directory):
        """Constructor.

        Parameters
        ----------
        repo : str
            The repo for the image (e.g. mvpstudio/base).

        version : int
            The version of the container to build and push.

        deps : list of str
            A list of other containers upon which this one depends. Can be either just a repo name (e.g. mvpstudio/base)
            or a name and a version (e.g. mvpstudio/base:v001). In the former case we'll find the container.yml file for
            the image in it's directory in this repo and use that as the version for the dependency.

        directory : pathlib.Path
            Path to the directory holding the container.yml and Dockerfile.template files.
        """
        self.repo = repo
        self.version = version
        self.deps = deps
        self.directory = directory


def stringify_version(to_build):
    return '%04d' % to_build.version


def build_one(to_build):
    """Sets up the context, filling in the template information from Dockerfile.template, and runs docker build.

    Parameters
    ----------
    to_build : ImageToBuild
        The image we should build.
    """
    log.info('Building %s:%s', to_build.repo, stringify_version(to_build))
    pass


def do_builds(to_build, no_deps):
    if no_deps:
        ready = copy.copy(to_build)
        to_build = {}
    else:
        ready = {}
        for candidate in to_build.values():
            if len(candidate.deps) == 0:
                log.info('%s has no dependencies and can be built immediately', candidate.repo)
                ready[candidate.repo] = candidate
        for r in ready.keys():
            del to_build[r]

    built = set()
    while len(ready) > 0:
        next_build = next(iter(ready.values()))
        build_one(next_build)
        built.add(next_build)
        del ready[next_build.repo]

        # The following is far less efficient than it might be but it shouldn't matter.
        for candidate in to_build.values():
            not_built_yet = [x for x in candidate.deps if x not in built]
            if len(not_built_yet) > 0:
                log.debug('%s is still not ready as %s have not been built yet', candidate.repo, not_built_yet)
            else:
                log.info('%s is now ready to be built.', candidate.repo)
                ready[candidate.repo] = candidate
                del to_build[candidate.repo]

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
    for contianer_file in THIS_DIR.glob('*/container.yml'):
        log.info('Parsing %s', contianer_file)
        with contianer_file.open() as inf:
            cd = yaml.load(inf, Loader=yaml.SafeLoader)
            all_containers[cd['repo']] = ImageToBuild(directory=contianer_file.parent, **cd)

    # to_build is like all_containers but contains only the images we actually want to build.
    to_build = {}
    if args.only is not None:
        only_set = set(args.only)
        to_build = {r: c for r, c in all_containers.items() if r in only_set}
    else:
        to_build = copy.copy(all_containers)
    print('to_build', to_build)

    do_builds(to_build, args.no_depends)


if __name__ == '__main__':
    main()
