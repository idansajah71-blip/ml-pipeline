import useSWR from 'swr';
import { datasets, models, experiments, abTests, monitoring, algorithms } from './api';
import { Dataset, MLModel, Experiment, ABTest, Stats } from '@/types';

const datasetsFetcher = async () => {
  const res = await datasets.list();
  return Array.isArray(res.data) ? res.data : [];
};

const modelsFetcher = async () => {
  const res = await models.list();
  return res.data.items;
};

const experimentsFetcher = async () => {
  const res = await experiments.list();
  return res.data.items;
};

const abTestsFetcher = async () => {
  const res = await abTests.list();
  return res.data.items;
};

const statsFetcher = async () => {
  const res = await monitoring.stats();
  return res.data;
};

const systemFetcher = async () => {
  const res = await monitoring.system();
  return res.data;
};

const algorithmsFetcher = async () => {
  const res = await algorithms.list();
  return res.data;
};

const datasetFetcher = async (id: string) => {
  const res = await datasets.get(id);
  return res.data;
};

const datasetPreviewFetcher = async (id: string) => {
  const res = await datasets.preview(id);
  return res.data;
};

const modelFetcher = async (id: string) => {
  const res = await models.get(id);
  return res.data;
};

export function useDatasets() {
  const { data, error, isLoading, mutate } = useSWR<Dataset[]>('datasets', datasetsFetcher, {
    revalidateOnFocus: true,
    revalidateOnReconnect: true,
  });
  return { datasets: data ?? [], isLoading, isError: error, mutate };
}

export function useDataset(id: string | undefined) {
  const { data, error, isLoading, mutate } = useSWR<Dataset>(
    id ? `dataset-${id}` : null,
    () => datasetFetcher(id!),
    { revalidateOnFocus: true }
  );
  return { dataset: data ?? null, isLoading, isError: error, mutate };
}

export function useDatasetPreview(id: string | undefined) {
  const { data, error, isLoading } = useSWR(
    id ? `dataset-preview-${id}` : null,
    () => datasetPreviewFetcher(id!),
    { revalidateOnFocus: false }
  );
  return { preview: data ?? null, isLoading, isError: error };
}

export function useModels() {
  const { data, error, isLoading, mutate } = useSWR<MLModel[]>('models', modelsFetcher, {
    revalidateOnFocus: true,
    revalidateOnReconnect: true,
  });
  return { models: data ?? [], isLoading, isError: error, mutate };
}

export function useModel(id: string | undefined) {
  const { data, error, isLoading, mutate } = useSWR<MLModel>(
    id ? `model-${id}` : null,
    () => modelFetcher(id!),
    { revalidateOnFocus: true }
  );
  return { model: data ?? null, isLoading, isError: error, mutate };
}

export function useExperiments() {
  const { data, error, isLoading, mutate } = useSWR<Experiment[]>('experiments', experimentsFetcher, {
    revalidateOnFocus: true,
    revalidateOnReconnect: true,
  });
  return { experiments: data ?? [], isLoading, isError: error, mutate };
}

export function useABTests() {
  const { data, error, isLoading, mutate } = useSWR<ABTest[]>('ab-tests', abTestsFetcher, {
    revalidateOnFocus: true,
    revalidateOnReconnect: true,
  });
  return { tests: data ?? [], isLoading, isError: error, mutate };
}

export function useStats() {
  const { data, error, isLoading } = useSWR<Stats>('stats', statsFetcher, {
    revalidateOnFocus: true,
    refreshInterval: 30000,
  });
  return { stats: data ?? null, isLoading, isError: error };
}

export function useSystem() {
  const { data, error, isLoading } = useSWR('system', systemFetcher, {
    revalidateOnFocus: true,
    refreshInterval: 30000,
  });
  return { system: data ?? null, isLoading, isError: error };
}

export function useAlgorithms() {
  const { data, error, isLoading } = useSWR('algorithms', algorithmsFetcher, {
    revalidateOnFocus: false,
  });
  return { algorithms: data?.algorithms ?? [], defaultParams: data?.default_params ?? {}, isLoading, isError: error };
}
