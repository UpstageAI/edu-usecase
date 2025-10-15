import { Outlet } from "react-router-dom";
import Header from "@/components/layout/Header";

const DefaultLayout = () => (
  <div className="bg-background flex h-screen overflow-hidden">
    <div className="flex flex-1 flex-col">
      <div className="bg-background sticky top-0 z-10">
        <Header />
      </div>
      <main className="relative flex flex-1 flex-col items-center justify-center overflow-hidden">
        <div className="flex h-full w-full flex-1 overflow-y-auto">
          <Outlet />
        </div>
      </main>
    </div>
  </div>
);

export default DefaultLayout;
