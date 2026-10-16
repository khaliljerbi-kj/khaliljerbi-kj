import type { Metadata } from "next";

import { SearchExperience } from "@/components/search/search-experience";

export const metadata: Metadata = { title: "Recherche · Paris Immo IA" };

export default function SearchPage() {
  return <SearchExperience />;
}
