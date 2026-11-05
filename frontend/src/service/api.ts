export interface Subblock {
  type: 'text' | 'technical';
  lines: string[];
}

export interface Block {
  program_name: string;
  pg_index: string;
  subblocks: Subblock[];
}

export interface Program {
  name: string;
  blocks: Block[];
}

export interface SlugsResponse {
  programs: Program[];
}

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:3000';

export async function postSlugs(
  arquivo: File,
): Promise<SlugsResponse> {
  const formData = new FormData();
  formData.append('file', arquivo);

  const response = await fetch(`${API_URL}/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    const message =
      typeof errorBody?.erro === 'string'
        ? errorBody.erro
        : `Erro ao enviar roteiro: ${response.status}`;

    throw new Error(message);
  }

  return response.json() as Promise<SlugsResponse>;
}