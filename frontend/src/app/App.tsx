// AI contribution: 50% or more AI-generated
/**
 * Every route of the app, one module per area in routes/ (FIX-13). A story adds
 * its screen's route to its area's module and its tab to navigation.ts; screens
 * that are not built yet have no route. Who may open each area comes from
 * shared/auth/roles.ts.
 */
import { Routes } from "react-router";

import { householdRoutes } from "./routes/householdRoutes";
import { publicRoutes } from "./routes/publicRoutes";
import { staffRoutes } from "./routes/staffRoutes";
import { storeRoutes } from "./routes/storeRoutes";

export default function App() {
  return (
    <Routes>
      {publicRoutes}
      {householdRoutes}
      {storeRoutes}
      {staffRoutes}
    </Routes>
  );
}
