import app from "./app";
import { config } from "@/config";

const PORT = config.port;

app.listen(PORT, () => {
  console.log(`Express server running on http://localhost:${PORT}`);
  console.log(`Environment: ${config.environment}`);
});
