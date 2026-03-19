export function getPaginationParams(searchParams: URLSearchParams) {
  const page = Math.max(1, Number(searchParams.get("page") ?? "1") || 1);
  const pageSize = Math.min(50, Math.max(1, Number(searchParams.get("pageSize") ?? "10") || 10));
  const skip = (page - 1) * pageSize;

  return { page, pageSize, skip };
}
