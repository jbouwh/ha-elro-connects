FROM mcr.microsoft.com/devcontainers/python:3.14

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Uninstall pre-installed formatting and linting tools
# They would conflict with our pinned versions
RUN \
    pipx uninstall pydocstyle \
    && pipx uninstall pycodestyle \
    && pipx uninstall mypy \
    && pipx uninstall pylint

# System libraries needed to run Home Assistant with default_config
RUN \
    apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        ffmpeg \
        libpcap-dev \
        libturbojpeg0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Add go2rtc binary, use the version recommended by the go2rtc integration
COPY --from=ghcr.io/alexxit/go2rtc:1.9.14 /usr/local/bin/go2rtc /bin/go2rtc

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
