// Material Symbols Outlined, as in the Stitch design. index.html loads only the glyphs listed
// in ICONS (Google Fonts' icon_names subset), so add new names there too.
export function Icon({
  name,
  className = "",
  fill = false,
  title,
}: {
  name: string;
  className?: string;
  fill?: boolean;
  title?: string;
}) {
  return (
    <span
      className={`material-symbols-outlined ${className}`}
      style={fill ? { fontVariationSettings: '"FILL" 1, "wght" 400, "GRAD" 0, "opsz" 24' } : undefined}
      aria-hidden={title ? undefined : true}
      title={title}
    >
      {name}
    </span>
  );
}
