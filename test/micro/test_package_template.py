import inspect
from io import StringIO
from textwrap import dedent
from typing import Optional, Type

import pytest
from conan.internal.model.options import Options
from conan.internal.model.profile import Profile

from cci_build.template.render import render_packages


class TestPackageTemplate:

    @staticmethod
    def create_linux_profile() -> Profile:

        profile = Profile()

        profile.settings["os"] = "Linux"
        profile.settings["compiler"] = "gcc"
        profile.settings["compiler.version"] = "14"

        profile.options = Options(options_values={
            "*": {
                "shared": "False"
            }
        })
        return profile

    @staticmethod
    def create_windows_profile() -> Profile:
        profile = Profile()

        profile.settings["os"] = "Windows"
        profile.settings["compiler"] = "msvc"
        profile.settings["compiler.version"] = "194"
        profile.settings["compiler.cppstd"] = "20"
        profile.settings["arch"] = "x86_64"
        profile.settings["build_type"] = "Release"

        profile.options = Options(options_values={
            "*": {
                "shared": "False"
            }
        })

        return profile

    @pytest.mark.parametrize(
        "input_package_list_template, build_profile, host_profile, expected_value, expected_exception",
        [
            # Check an empty template renders ok
            ("", create_linux_profile(), create_linux_profile(), "", None),

            # render a simple template variable
            ("{{ b.settings.os }}", create_linux_profile(), create_windows_profile(), "Linux", None),
            ("{{ h.settings.os }}", create_linux_profile(), create_windows_profile(), "Windows", None),


            # render multiple settings, including nested values
            (dedent("""
            {{ h.settings.os }}
            {{ h.settings.compiler }}
            {{ h.settings.compiler.version }}
            {{ h.settings.build_type }}
            """),
             create_linux_profile(),
             create_windows_profile(),
             dedent("""
             Windows
             msvc
             194
             Release"""), None),

            # Render a conditional block
            (dedent("""
            {% if h.settings.os == 'Windows' %}
            windows-package/1.2.3
            {% elif h.settings.os == 'Linux' %}
            linux-package/4.5.6
            {% else %}
            other-package/7.8.9
            {% endif %}
            """),
             create_linux_profile(),
             create_windows_profile(),
             dedent("""

             windows-package/1.2.3
             """), None),
        ])
    def test_package_template(
            self,
            input_package_list_template: str,
            build_profile: Profile,
            host_profile: Profile,
            expected_value: str,
            expected_exception: Optional[Type[Exception]]):
        """
            Test that a package list template is rendered correctly
        """
        with StringIO(input_package_list_template) as io:
            if expected_exception:
                with pytest.raises(expected_exception):
                    result = render_packages(io, build_profile, host_profile)
            else:
                result = render_packages(io, build_profile, host_profile)
                assert expected_value == result
