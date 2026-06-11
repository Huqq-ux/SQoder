import pytest
from Coder.storage.course_manager import CourseManager


@pytest.mark.asyncio
async def test_create_and_get_course():
    course_id = await CourseManager.create_course(
        name="高等数学",
        description="大一上学期",
        semester="2025-秋季"
    )
    assert course_id is not None

    course = await CourseManager.get_course(course_id)
    assert course is not None
    assert course["name"] == "高等数学"
    assert course["description"] == "大一上学期"

    await CourseManager.delete_course(course_id)


@pytest.mark.asyncio
async def test_list_courses():
    id1 = await CourseManager.create_course(name="课程A")
    id2 = await CourseManager.create_course(name="课程B")

    courses = await CourseManager.list_courses()
    names = [c["name"] for c in courses]

    await CourseManager.delete_course(id1)
    await CourseManager.delete_course(id2)

    assert "课程A" in names
    assert "课程B" in names


@pytest.mark.asyncio
async def test_add_knowledge_point():
    course_id = await CourseManager.create_course(name="测试知识点课程")
    kp_id = await CourseManager.add_knowledge_point(
        course_id=course_id,
        name="极限的定义",
        section="第一章 §1.1",
        chunk_content="设函数f(x)在点x0的某个去心邻域内有定义...",
        source_file="高数上册.pdf",
        source_page=12
    )
    assert kp_id is not None

    points = await CourseManager.get_knowledge_points(course_id)
    assert len(points) > 0
    assert points[0]["name"] == "极限的定义"

    await CourseManager.delete_course(course_id)


@pytest.mark.asyncio
async def test_register_course_file():
    course_id = await CourseManager.create_course(name="文件注册测试")
    file_id = await CourseManager.register_file(
        course_id=course_id,
        filename="课件第一章.pptx",
        file_type="pptx",
        file_size=2048000,
        chunk_count=15,
        index_path="/data/indexes/course_abc"
    )
    assert file_id is not None

    files = await CourseManager.list_files(course_id)
    assert len(files) > 0
    assert files[0]["filename"] == "课件第一章.pptx"

    await CourseManager.delete_course(course_id)
