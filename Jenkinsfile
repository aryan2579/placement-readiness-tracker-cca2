pipeline {
    agent any
    options { timestamps(); disableConcurrentBuilds() }
    environment {
        IMAGE_NAME = 'placement-readiness-tracker'
        // Create these Jenkins credentials before running the pipeline.
        DOCKERHUB_CREDENTIALS = credentials('dockerhub-credentials')
    }
    stages {
        stage('Checkout') {
            steps { checkout scm }
        }
        stage('Install Dependencies and Test') {
            steps {
                sh '''
                    python3 -m venv .venv
                    . .venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                    pytest -q --junitxml=pytest-results.xml
                '''
            }
        }
        stage('Build Docker Image') {
            steps {
                sh '''
                    docker build -t ${DOCKERHUB_CREDENTIALS_USR}/${IMAGE_NAME}:${BUILD_NUMBER} .
                    docker tag ${DOCKERHUB_CREDENTIALS_USR}/${IMAGE_NAME}:${BUILD_NUMBER} ${DOCKERHUB_CREDENTIALS_USR}/${IMAGE_NAME}:latest
                '''
            }
        }
        stage('Push Image to Docker Hub') {
            steps {
                sh '''
                    echo "$DOCKERHUB_CREDENTIALS_PSW" | docker login -u "$DOCKERHUB_CREDENTIALS_USR" --password-stdin
                    docker push ${DOCKERHUB_CREDENTIALS_USR}/${IMAGE_NAME}:${BUILD_NUMBER}
                    docker push ${DOCKERHUB_CREDENTIALS_USR}/${IMAGE_NAME}:latest
                    docker logout
                '''
            }
        }
        stage('Deploy to Minikube') {
            steps {
                sh '''
                    kubectl apply -f k8s/service.yaml
                    kubectl apply -f k8s/deployment.yaml
                    kubectl set image deployment/placement-readiness-tracker web=${DOCKERHUB_CREDENTIALS_USR}/${IMAGE_NAME}:${BUILD_NUMBER}
                    kubectl rollout status deployment/placement-readiness-tracker --timeout=180s
                '''
            }
        }
        stage('Verify Deployment') {
            steps {
                sh '''
                    kubectl get deployment, pods, service -l app=placement-readiness-tracker
                    kubectl get service placement-readiness-tracker
                '''
            }
        }
    }
    post {
        always { junit allowEmptyResults: true, testResults: 'pytest-results.xml' }
        success { echo 'Pipeline passed: tests, image build/push, deployment and rollout completed.' }
        failure { echo 'Pipeline failed. Review the stage logs before submitting screenshots.' }
    }
}
