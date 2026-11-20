# Katip relay for ChatGPT: a remote MCP server that holds encrypted masked text for 15 minutes (RAM only)
# and runs the research tools (emsal_ara, mevzuat_bak, geri_bildirim). No model, no OCR: masking happens
# on the lawyer's device, never here.
FROM python:3.12-slim
RUN pip install --no-cache-dir cryptography==50.0.2 && useradd -m -u 1000 katip
WORKDIR /app
COPY --chown=katip katip_kalkan/ /app/katip_kalkan/
USER katip
ENV PORT=7860 KATIP_HOME=/tmp/katip KATIP_EMSAL_ONLINE=1 KATIP_LOG=INFO PYTHONUNBUFFERED=1
EXPOSE 7860
CMD ["python", "-m", "katip_kalkan.relay", "--host", "0.0.0.0"]
