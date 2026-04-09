FROM oven/bun:1
WORKDIR /app

# Copy package files and install deps
COPY package.json bun.lock* ./
RUN bun install

# Copy source
COPY src/ src/

EXPOSE 3000

CMD ["bun", "run", "src/index.ts"]
