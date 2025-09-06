import { redirect } from "next/navigation";

export default function RepoPage() {
  redirect("/library?tab=repo");
  return null;
}
