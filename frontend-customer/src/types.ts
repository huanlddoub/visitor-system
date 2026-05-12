export type RequirementType = "general" | "pickup" | "dropoff" | "hotel" | "meal";

export interface RequirementCreate {
  type: RequirementType;
  detail: Record<string, unknown>;
}

export interface VisitorCreate {
  name: string;
  company: string;
  phone: string;
  visit_time: string;
  people_count: number;
  remark?: string;
  requirements: RequirementCreate[];
}

export interface VisitorOut extends VisitorCreate {
  id: number;
  status: string;
  created_at: string;
  updated_at: string;
}
