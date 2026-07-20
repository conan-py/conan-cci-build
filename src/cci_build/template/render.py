"""
    Support for rendering 'packages.txt' as a jinja template.
"""
import os
from io import TextIOWrapper

from conan.internal.model.profile import Profile
from jinja2 import Environment

from cci_build.template.profile_proxy import ProfileProxy


def render_packages(packages: TextIOWrapper, build_profile: Profile, host_profile: Profile) -> str:
    """
        Render a package list jinja template from a stream

        :return: a string with the rendered template
    """
    jinja2_env = Environment()

    template = jinja2_env.from_string(packages.read())
    return template.render(b=ProfileProxy(build_profile), h=ProfileProxy(host_profile), os=os)
