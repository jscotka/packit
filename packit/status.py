import logging
from tabulate import tabulate

from packit.config import Config, PackageConfig
from packit.distgit import DistGit
from packit.exceptions import PackitException
from packit.upstream import Upstream

logger = logging.getLogger(__name__)


class Status:
    """
    This class provides methods to obtain status of the package
    """

    def __init__(self, config: Config, package_config: PackageConfig):
        self.config = config
        self.package_config = package_config

        self.up = Upstream(config=self.config, package_config=self.package_config)
        self.dg = DistGit(config=self.config, package_config=self.package_config)

    def get_downstream_prs(self, number_of_prs: int = 5) -> None:
        """
        Get specific number of latest downstream PRs
        :param number_of_prs: int
        :return: None
        """
        pr_list = self.dg.local_project.git_project.get_pr_list()
        if len(pr_list) > 0:
            # take last `number_of_prs` PRs
            pr_list = (
                pr_list[:number_of_prs] if len(pr_list) > number_of_prs else pr_list
            )
            logger.info("Downstream PRs:")
            table = [[pr.id, pr.title, pr.url] for pr in pr_list]
            logger.info(tabulate(table, headers=["ID", "Title", "URL"]))
        else:
            logger.info("Downstream PRs: No open PRs.")

    def get_dg_versions(self) -> None:
        """
        Get versions from all branches in Dist-git
        :return: None
        """
        branches = self.dg.local_project.git_project.get_branches()
        for branch in branches:
            try:
                self.dg.create_branch(
                    branch, base=f"remotes/origin/{branch}", setup_tracking=False
                )
                self.dg.checkout_branch(branch)
            except Exception as ex:
                logger.debug(f"Branch {branch} is not present: {ex}")
                continue
            try:
                logger.info(f"{branch}: {self.dg.specfile.get_version()}")
            except PackitException:
                logger.debug(f"Can't figure out the version of branch: {branch}")
        self.dg.checkout_branch("master")

    def get_up_releases(self, number_of_releases: int = 5) -> None:
        """
        Get specific number of latest upstream releases
        :param number_of_releases: int
        :return: None
        """
        latest_releases = self.up.local_project.git_project.get_releases()
        if len(latest_releases) > 0:
            logger.info("\nGitHub upstream releases:")
            # take last five releases
            latest_releases = (
                latest_releases[:number_of_releases]
                if len(latest_releases) > number_of_releases
                else latest_releases
            )
            upstream_releases_str = "\n".join(
                f"{release.tag_name}" for release in latest_releases
            )
            logger.info(upstream_releases_str)
        else:
            logger.info("\nGitHub upstream releases: No releases found.")

    def get_builds(self, number_of_builds: int = 3) -> None:
        """
        Get specific number of latest builds from koji
        :param number_of_builds: int
        :return: None
        """
        logger.info("\nLatest builds:")
        # https://github.com/fedora-infra/bodhi/issues/3058
        from bodhi.client.bindings import BodhiClient

        b = BodhiClient()
        builds_d = b.latest_builds(self.dg.package_name)

        branches = self.dg.local_project.git_project.get_branches()
        branches.remove("master")  # there is no master tag in koji
        for branch in branches:
            koji_tag = f"{branch}-updates-candidate"
            try:
                koji_builds = [builds_d[koji_tag]]
                # take last three builds
                koji_builds = (
                    koji_builds[:number_of_builds]
                    if len(koji_builds) > number_of_builds
                    else koji_builds
                )
                koji_builds_str = "\n".join(f" - {b}" for b in koji_builds)
                logger.info(f"{branch}:\n{koji_builds_str}")
            except KeyError:
                logger.info(f"{branch}: No builds.")

    def get_updates(self, number_of_updates: int = 3) -> None:
        """
        Get specific number of latest updates in bodhi
        :param number_of_updates: int
        :return: None
        """
        logger.info("\nLatest bodhi updates:")
        # https://github.com/fedora-infra/bodhi/issues/3058
        from bodhi.client.bindings import BodhiClient

        b = BodhiClient()
        results = b.query(packages=self.dg.package_name)["updates"]
        if len(results) > number_of_updates:
            results = results[:number_of_updates]

        table = [
            [result["title"], result["karma"], result["status"]] for result in results
        ]
        logger.info(tabulate(table, headers=["Update", "Karma", "status"]))
