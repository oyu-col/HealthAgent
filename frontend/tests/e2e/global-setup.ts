import { createServer } from "vite";

/** Own and close Vite in-process; Windows shell descendants can hang webServer teardown. */
export default async function setup() {
  const server = await createServer({
    server: { host: "127.0.0.1", port: 5173, strictPort: true },
  });
  try {
    await server.listen();
  } catch (cause) {
    await server.close();
    throw cause;
  }
  return async () => {
    await server.close();
  };
}
