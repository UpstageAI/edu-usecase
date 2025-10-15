import { RouteObject } from "react-router-dom";
import DefaultLayout from "@/layouts/DefaultLayout";
import Home from "@/pages/Home";
import Upload from "@/pages/Upload";
import Analysis from "@/pages/Analysis";
import DocumentInsights from "@/pages/DocumentInsights";
import NotFound from "@/pages/NotFound";

export const routes: RouteObject[] = [
  {
    path: "/",
    element: <DefaultLayout />,
    children: [
      { index: true, element: <Home /> },
      { path: "upload", element: <Upload /> },
      { path: "analysis", element: <Analysis /> },
      { path: "analysis/:documentId", element: <DocumentInsights /> },
    ],
  },
  { path: "*", element: <NotFound /> },
];
