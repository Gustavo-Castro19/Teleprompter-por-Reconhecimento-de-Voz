import { useEffect, useState } from "react";
import {
  loadSlugs,
  SLUGS_STORAGE_KEY,
  SLUGS_UPDATED_EVENT,
} from "../lib/slugsStorage";
import type { Program } from "../service/api";

export function useSlugs(): Program[] {
  const [programs, setPrograms] = useState<Program[]>(
    () => loadSlugs()?.programs ?? [],
  );

  useEffect(() => {
    function refresh() {
      setPrograms(loadSlugs()?.programs ?? []);
    }

    function onStorage(event: StorageEvent) {
      if (event.key !== SLUGS_STORAGE_KEY) return;
      refresh();
    }

    window.addEventListener(SLUGS_UPDATED_EVENT, refresh);
    window.addEventListener("storage", onStorage);

    return () => {
      window.removeEventListener(SLUGS_UPDATED_EVENT, refresh);
      window.removeEventListener("storage", onStorage);
    };
  }, []);

  return programs;
}
