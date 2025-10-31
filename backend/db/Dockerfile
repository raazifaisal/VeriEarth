FROM postgis/postgis:17-3.4

USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends gnupg curl ca-certificates lsb-release \
    && sh -c "echo deb https://packagecloud.io/timescale/timescaledb/debian/ $(lsb_release -cs) main > /etc/apt/sources.list.d/timescaledb.list" \
    && curl -L https://packagecloud.io/timescale/timescaledb/gpgkey | apt-key add - \
    && apt-get update \
    && apt-get install -y --no-install-recommends timescaledb-2-postgresql-17 \
    && rm -rf /var/lib/apt/lists/*

USER postgres


