# 行政手続LOD の SPARQL サーバー(Oxigraph、読むだけ)。
# 中身をイメージに入れる形: イメージを作るときに data/rdf の Turtle から店を作り、最後のイメージに店だけを写す。
# 手元に Docker が無くても、Cloud Build で作れる(deploy.md の手順 3)。
FROM debian:bookworm-slim AS build
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 libssl3 ca-certificates && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/oxigraph/oxigraph:0.5.13 /usr/local/bin/oxigraph /usr/local/bin/oxigraph
COPY data/rdf/ /src/
RUN set -eu; \
    files="$(ls /src/*.ttl.gz) $(ls /src/weekly/*.ttl.gz 2>/dev/null || true)"; \
    oxigraph load --location /data --file $files; \
    oxigraph optimize --location /data

FROM ghcr.io/oxigraph/oxigraph:0.5.13
COPY --from=build /data /data
EXPOSE 8080
ENTRYPOINT ["/usr/local/bin/oxigraph"]
# --timeout-s: 1 つの問いの上限(秒)。Cloud Run の要求の上限(30 秒)より短くする
# --cors: GitHub Pages の閲覧ページ(view.html)から問い合わせるため
CMD ["serve-read-only", "--location", "/data", "--bind", "0.0.0.0:8080", "--timeout-s", "20", "--cors"]
