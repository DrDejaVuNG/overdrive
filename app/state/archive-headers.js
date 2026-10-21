// off-thread archive reads even in the case of native worker error
export async function inspectHeaders(archives, sources, why, log = console.log, now = Date.now) {
  const started = now();
  try {
    if (typeof archives?.inspectAsync !== "function" || archives.supportsAsyncInspection === false)
      throw new Error("Asynchronous archive inspection is unavailable. Update the PS5 React runtime (ABI v19).");
    const found = await archives.inspectAsync(sources);
    log(`[download-queue] header check (${why}): ${found.kind || "no known format"}${found.refusal ? `, refused: ${found.refusal}` : ""} in ${now() - started} ms (waited ${found.waitedMs ?? 0} ms, read ${found.tookMs ?? 0} ms)`);
    return found;
  } catch (error) {
    log(`[download-queue] header check (${why}) failed without synchronous retry: ${error.message}`);
    throw error;
  }
}

// Optional header checks must not fail completed downloads or prevent regular extraction.
export async function optionalHeaders(archives, sources, why) {
  try {
    return await inspectHeaders(archives, sources, why);
  } catch {
    return null;
  }
}
