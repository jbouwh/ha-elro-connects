FROM mcr.microsoft.com/devcontainers/python:3.14

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Uninstall pre-installed formatting and linting tools
# They would conflict with our pinned versions
RUN \
    pipx uninstall pydocstyle \
    && pipx uninstall pycodestyle \
    && pipx uninstall mypy \
    && pipx uninstall pylint

# Install uv
RUN pip3 install uv

WORKDIR /usr/src

USER vscode
ENV VIRTUAL_ENV="/home/vscode/.local/ic-venv"
RUN uv venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR /workspaces/ha-elro-connects

# Set the default shell to bash instead of sh
ENV SHELL=/bin/bash
RUN source $VIRTUAL_ENV/bin/activate
