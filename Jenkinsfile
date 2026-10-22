pipeline {
    agent {
        label 'windows'
    }

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    environment {
        IMAGE_NAME = 'aryan2020/placement-readiness-tracker'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Install Dependencies and Test') {
            steps {
                bat '''
                    python --version
                    python -m pip install -r requirements.txt
                    python -m pytest -q --junitxml=pytest-results.xml
                '''
            }
        }

        stage('Build Docker Image') {
            steps {
                bat '''
                    docker build -t %IMAGE_NAME%:%BUILD_NUMBER% .
                    docker tag %IMAGE_NAME%:%BUILD_NUMBER% %IMAGE_NAME%:latest
                '''
            }
        }

       stage('Push Image to Docker Hub') {
    steps {
        withCredentials([usernamePassword(
            credentialsId: 'dockerhub-credentials',
            usernameVariable: 'DH_USER',
            passwordVariable: 'DH_TOKEN'
        )]) {
            bat '''
                powershell -NoProfile -NonInteractive -Command "$env:DH_TOKEN | docker login -u $env:DH_USER --password-stdin"
                if errorlevel 1 exit /b 1
            '''

            bat '''
                docker push %IMAGE_NAME%:%BUILD_NUMBER%
                if errorlevel 1 exit /b 1
                docker push %IMAGE_NAME%:latest
                if errorlevel 1 exit /b 1
                docker logout
            '''
        }
    }
}

        stage('Deploy to Minikube') {
            steps {
                bat '''
                    kubectl apply -f k8s/service.yaml
                    kubectl apply -f k8s/deployment.yaml
                    kubectl set image deployment/placement-readiness-tracker web=%IMAGE_NAME%:%BUILD_NUMBER%
                    kubectl rollout status deployment/placement-readiness-tracker --timeout=180s
                '''
            }
        }

        stage('Verify Deployment') {
            steps {
                bat '''
                    kubectl get deployment,pods,service -l app=placement-readiness-tracker
                    kubectl get service placement-readiness-tracker
                '''
            }
        }
    }

    post {
        always {
            junit allowEmptyResults: true, testResults: 'pytest-results.xml'
        }
        success {
            echo 'CI/CD pipeline completed successfully!'
        }
        failure {
            echo 'Pipeline failed. Check the stage logs.'
        }
    }
}
