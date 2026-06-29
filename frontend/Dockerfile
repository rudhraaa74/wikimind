FROM node:18-alpine

WORKDIR /app

# Copy package files and install dependencies
COPY package*.json ./
RUN npm install

# Copy all frontend code
COPY . .

EXPOSE 5173

# Start the Vite dev server (bind to 0.0.0.0 so it's accessible outside the container)
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
