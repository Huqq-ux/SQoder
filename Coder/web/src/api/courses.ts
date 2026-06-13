import { api } from './client';

export interface Course {
  id: string;
  slug: string;
  name: string;
  description: string;
  semester: string;
  created_at: string;
  updated_at: string;
}

export interface KnowledgePoint {
  id: string;
  name: string;
  section: string;
  source_file: string;
  source_page: number;
}

export interface CourseFile {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  chunk_count: number;
  uploaded_at: string;
}

export async function listCourses(): Promise<Course[]> {
  const data = await api.get<{ courses: Course[] }>('/courses');
  return data.courses;
}

export async function getCourse(courseId: string): Promise<Course> {
  const data = await api.get<{ course: Course }>(`/courses/${courseId}`);
  return data.course;
}

export async function createCourse(
  name: string,
  description?: string,
  semester?: string
): Promise<string> {
  const data = await api.post<{ status: string; course_id: string }>('/courses', {
    name,
    description,
    semester,
  });
  return data.course_id;
}

export async function deleteCourse(courseId: string): Promise<void> {
  await api.del(`/courses/${courseId}`);
}

export async function getKnowledgePoints(
  courseId: string
): Promise<KnowledgePoint[]> {
  const data = await api.get<{ knowledge_points: KnowledgePoint[] }>(
    `/courses/${courseId}/knowledge-points`
  );
  return data.knowledge_points;
}

export async function getCourseFiles(courseId: string): Promise<CourseFile[]> {
  const data = await api.get<{ files: CourseFile[] }>(
    `/courses/${courseId}/files`
  );
  return data.files;
}

export async function updateKpProgress(
  courseId: string,
  kpId: string,
  status: 'unlearned' | 'learning' | 'mastered',
  masteryScore?: number,
): Promise<void> {
  const scoreMap = { unlearned: 0.0, learning: 0.5, mastered: 1.0 };
  await api.post(`/courses/${courseId}/progress`, {
    kp_id: kpId,
    status,
    mastery_score: masteryScore ?? scoreMap[status],
  });
}
