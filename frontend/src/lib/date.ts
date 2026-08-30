export interface FormattedDate {
  label: string;
  iso: string | null;
}

export function formatTicketDate(raw: string): FormattedDate {
  const parsed = new Date(raw);
  if (Number.isNaN(parsed.getTime())) {
    return { label: raw, iso: null };
  }
  return {
    label: parsed.toLocaleString("es-ES", {
      dateStyle: "medium",
      timeStyle: "short",
    }),
    iso: raw,
  };
}
