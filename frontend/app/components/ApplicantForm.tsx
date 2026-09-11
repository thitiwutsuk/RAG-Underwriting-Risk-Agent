"use client";

import { HEALTH_CONDITIONS, OCCUPATION_CLASSES, POLICY_TYPES } from "../lib/types";
import type { ApplicantForm as ApplicantFormData } from "../lib/types";

const inputClasses =
  "w-full rounded-md border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 shadow-sm focus:border-zinc-500 focus:outline-none focus:ring-1 focus:ring-zinc-500 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100";

const labelClasses = "mb-1 block text-sm font-medium text-zinc-700 dark:text-zinc-300";

interface Props {
  form: ApplicantFormData;
  onChange: (form: ApplicantFormData) => void;
  onSubmit: () => void;
  submitting: boolean;
}

export default function ApplicantForm({ form, onChange, onSubmit, submitting }: Props) {
  function set<K extends keyof ApplicantFormData>(key: K, value: ApplicantFormData[K]) {
    onChange({ ...form, [key]: value });
  }

  function toggleCondition(condition: string) {
    const has = form.health_conditions.includes(condition);
    if (condition === "None declared") {
      set("health_conditions", has ? [] : ["None declared"]);
      return;
    }
    const withoutNone = form.health_conditions.filter((c) => c !== "None declared");
    set(
      "health_conditions",
      has ? withoutNone.filter((c) => c !== condition) : [...withoutNone, condition]
    );
  }

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit();
      }}
      className="flex flex-col gap-6"
    >
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <label className={labelClasses}>Full name</label>
          <input
            className={inputClasses}
            required
            value={form.name}
            onChange={(e) => set("name", e.target.value)}
            placeholder="Jamie Anderson"
          />
        </div>
        <div>
          <label className={labelClasses}>Gender</label>
          <select
            className={inputClasses}
            value={form.gender}
            onChange={(e) => set("gender", e.target.value)}
          >
            <option value="">Prefer not to say</option>
            <option value="Female">Female</option>
            <option value="Male">Male</option>
            <option value="Other">Other</option>
          </select>
        </div>

        <div>
          <label className={labelClasses}>Age</label>
          <input
            type="number"
            min={0}
            max={120}
            required
            className={inputClasses}
            value={form.age}
            onChange={(e) => set("age", e.target.value)}
          />
        </div>
        <div className="flex items-end pb-2">
          <label className="flex items-center gap-2 text-sm text-zinc-700 dark:text-zinc-300">
            <input
              type="checkbox"
              checked={form.smoker}
              onChange={(e) => set("smoker", e.target.checked)}
            />
            Current smoker
          </label>
        </div>

        <div>
          <label className={labelClasses}>Height (cm)</label>
          <input
            type="number"
            className={inputClasses}
            value={form.height_cm}
            onChange={(e) => set("height_cm", e.target.value)}
          />
        </div>
        <div>
          <label className={labelClasses}>Weight (kg)</label>
          <input
            type="number"
            className={inputClasses}
            value={form.weight_kg}
            onChange={(e) => set("weight_kg", e.target.value)}
          />
        </div>

        <div>
          <label className={labelClasses}>BMI</label>
          <input
            type="number"
            step="0.1"
            required
            className={inputClasses}
            value={form.bmi}
            onChange={(e) => set("bmi", e.target.value)}
            placeholder="e.g. 23.4"
          />
        </div>
        <div>
          <label className={labelClasses}>Occupation class</label>
          <select
            required
            className={inputClasses}
            value={form.occupation_class}
            onChange={(e) => set("occupation_class", e.target.value)}
          >
            <option value="">Select a class</option>
            {OCCUPATION_CLASSES.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className={labelClasses}>Occupation (free text)</label>
          <input
            className={inputClasses}
            value={form.occupation}
            onChange={(e) => set("occupation", e.target.value)}
            placeholder="Teacher"
          />
        </div>
        <div>
          <label className={labelClasses}>Policy type requested</label>
          <select
            required
            className={inputClasses}
            value={form.policy_type_requested}
            onChange={(e) => set("policy_type_requested", e.target.value)}
          >
            <option value="">Select a policy type</option>
            {POLICY_TYPES.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className={labelClasses}>Coverage amount (USD)</label>
          <input
            type="number"
            className={inputClasses}
            value={form.coverage_amount_usd}
            onChange={(e) => set("coverage_amount_usd", e.target.value)}
            placeholder="100000"
          />
        </div>
      </div>

      <div>
        <label className={labelClasses}>Declared health conditions</label>
        <div className="grid grid-cols-1 gap-x-4 gap-y-2 rounded-md border border-zinc-200 p-3 sm:grid-cols-2 dark:border-zinc-800">
          {HEALTH_CONDITIONS.map((condition) => (
            <label
              key={condition}
              className="flex items-center gap-2 text-sm text-zinc-700 dark:text-zinc-300"
            >
              <input
                type="checkbox"
                checked={form.health_conditions.includes(condition)}
                onChange={() => toggleCondition(condition)}
              />
              {condition}
            </label>
          ))}
        </div>
      </div>

      <button
        type="submit"
        disabled={submitting}
        className="w-full rounded-md bg-zinc-900 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-zinc-700 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300"
      >
        {submitting ? "Assessing…" : "Run underwriting assessment"}
      </button>
    </form>
  );
}
