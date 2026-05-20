import { Navigate, Route, Routes } from "react-router-dom";
import Layout from "@/components/Layout";
import HomePage from "@/features/home/HomePage";
import JobWorkspacePage from "@/features/job/JobWorkspacePage";
import CandidatePage from "@/features/candidate/CandidatePage";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="jobs/:jobId" element={<JobWorkspacePage />} />
        <Route path="candidate" element={<CandidatePage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
