# Use the official Kroki image
FROM yuzutech/kroki:latest

# Expose the default port
EXPOSE 8000

# Set environment variables if needed
# KROKI_SSL_SUPPORT is not needed for Cloud Run as SSL is terminated at the load balancer
ENV KROKI_PORT=8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=3s \
  CMD curl -f http://localhost:8000/health || exit 1
