import Image from "next/image";

export function UserAvatar({ src, alt }: { src?: string | null; alt: string }) {
  if (src) {
    return <Image src={src} alt={alt} width={40} height={40} className="rounded-full border border-border" />;
  }

  return (
    <div className="flex h-10 w-10 items-center justify-center rounded-full border border-border bg-secondary text-sm font-semibold text-foreground">
      {alt.slice(0, 2).toUpperCase()}
    </div>
  );
}
