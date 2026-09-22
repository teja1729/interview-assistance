import { redirect } from "next/navigation";

// Retire old invitation links without exposing membership management.
export default function InvitePage() {
  redirect("/settings");
}
