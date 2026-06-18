"use client";

import { useState } from "react";
import { Button } from "@wellbe/ui";
import { CaptureModal } from "@/components/capture/CaptureModal";

/** "Add event" on a thread timeline — opens the real capture flow (WEL-155). */
export function AddEventButton() {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button variant="ghost" size="sm" icon="plus" onClick={() => setOpen(true)}>
        Add event
      </Button>
      {open && <CaptureModal onClose={() => setOpen(false)} />}
    </>
  );
}
