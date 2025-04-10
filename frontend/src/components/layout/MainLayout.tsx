import { ReactNode } from "react";
import TabBar from "./TabBar";
import NavHeader from "./NavHeader";

interface MainLayoutProps {
  children: ReactNode;
}

const MainLayout = ({ children }: MainLayoutProps) => {
  return (
    <div className="min-h-screen bg-background flex flex-col">
      <NavHeader />
      <main className="flex-1 container max-w-4xl mx-auto px-4 py-8 pb-24">
        {children}
      </main>
      <TabBar />
    </div>
  );
};

export default MainLayout;
