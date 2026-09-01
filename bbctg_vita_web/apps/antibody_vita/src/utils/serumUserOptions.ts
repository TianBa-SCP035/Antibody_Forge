import { fetchSerumUserOptions } from '#/api/serum';

let cachedUserNames: string[] | null = null;
let userNamesRequest: Promise<string[]> | null = null;

function uniqueNames(values: Array<string | null | undefined>) {
  return [
    ...new Set(
      values.map((item) => String(item || '').trim()).filter(Boolean),
    ),
  ];
}

export function getCachedSerumUserOptions(): string[] {
  return cachedUserNames || [];
}

export async function loadSerumUserOptions(): Promise<string[]> {
  if (cachedUserNames) return cachedUserNames;
  if (!userNamesRequest) {
    userNamesRequest = fetchSerumUserOptions()
      .then((data) => {
        cachedUserNames = uniqueNames(data?.items || []);
        return cachedUserNames;
      })
      .finally(() => {
        userNamesRequest = null;
      });
  }
  return userNamesRequest;
}

export { uniqueNames };
