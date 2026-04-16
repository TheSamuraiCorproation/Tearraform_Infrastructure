# Simple Logstash image that copies a pipeline and rules into /usr/share/logstash/pipeline
FROM docker.elastic.co/logstash/logstash:8.9.0

# create pipeline dir and copy pipeline + rules
USER root
COPY pipeline/ /usr/share/logstash/pipeline/
COPY config/logstash.yml /usr/share/logstash/config/logstash.yml

# ensure permissions
RUN chown -R logstash:logstash /usr/share/logstash/pipeline /usr/share/logstash/config

USER logstash
