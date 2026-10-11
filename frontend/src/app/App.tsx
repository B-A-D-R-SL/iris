// AI contribution: 50% or more AI-generated
import { Route, Routes } from "react-router";
import { HomePage } from "../pages/HomePage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
    </Routes>
  );
}
