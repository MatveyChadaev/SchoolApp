#include "lesson.h"
#include "ui_lesson.h"

Lesson::Lesson(QWidget *parent, QString lesson, QString time, QString cab)
    : QWidget(parent)
    , ui(new Ui::Lesson)
{
    ui->setupUi(this);

    ui->lbl_lesson->setText(lesson);
    ui->lbl_time->setText(time);
    ui->lbl_cab->setText(cab);
}

Lesson::~Lesson()
{
    delete ui;
}
