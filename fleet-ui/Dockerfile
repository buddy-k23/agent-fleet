FROM node:20-alpine AS build

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .

# Bake env vars into the build
ARG VITE_SUPABASE_URL=http://localhost:54321
ARG VITE_SUPABASE_ANON_KEY
ARG VITE_API_BASE=http://localhost:8000
ENV VITE_SUPABASE_URL=$VITE_SUPABASE_URL
ENV VITE_SUPABASE_ANON_KEY=$VITE_SUPABASE_ANON_KEY
ENV VITE_API_BASE=$VITE_API_BASE

# Polyfill CustomEvent for Node.js (@xyflow/react needs it)
RUN echo "if(!globalThis.CustomEvent){globalThis.CustomEvent=class extends Event{constructor(e,t={}){super(e,t);this.detail=t.detail}}}" > /tmp/polyfill.js
RUN node -r /tmp/polyfill.js ./node_modules/.bin/vite build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 3001
CMD ["nginx", "-g", "daemon off;"]
