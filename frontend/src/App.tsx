import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import MainLayout from "@/components/layout/MainLayout";
import Home from "./pages/Home";
import Translate from "./pages/Translate";
import Contribute from "./pages/Contribute";
import Rewards from "./pages/Rewards";
import Learn from "./pages/Learn";
import Profile from "./pages/Profile";
import { WagmiConfig } from "wagmi";
import { wagmiConfig } from "@/lib/wagmi";

function App() {
  return (
    <Router>
      <WagmiConfig config={wagmiConfig}>
        <MainLayout>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/translate" element={<Translate />} />
            <Route path="/contribute" element={<Contribute />} />
            <Route path="/rewards" element={<Rewards />} />
            <Route path="/learn" element={<Learn />} />
            <Route path="/profile" element={<Profile />} />
          </Routes>
        </MainLayout>
      </WagmiConfig>
    </Router>
  );
}

export default App;
